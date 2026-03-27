---
id: live/coguest-apply
platform: ios
---

# 观众申请连麦 — iOS 实现

## 前置条件

**依赖安装（Podfile）**
```ruby
pod 'AtomicXCore', '~> 4.0'
```

**Info.plist 权限声明**（连麦需要摄像头与麦克风权限）
```xml
<key>NSCameraUsageDescription</key>
<string>连麦时需要访问摄像头</string>
<key>NSMicrophoneUsageDescription</key>
<string>连麦时需要访问麦克风</string>
```

**前置状态**：
- `LoginStore.shared.isLogin == true`（登录成功）
- 已进入直播间，持有有效的 `liveID`
- `CoGuestStore` 已通过 `create(liveID:)` 初始化

## API 调用

```swift
// ── 初始化 ─────────────────────────────────────────────────────
CoGuestStore.create(liveID: String) -> CoGuestStore

// ── 观众端 ─────────────────────────────────────────────────────
// 发起连麦申请；timeout 单位为秒，推荐 30
coGuestStore.applyForSeat(
    timeout: Double,
    extraInfo: String?,
    completion: ((Result<Void, CoGuestError>) -> Void)?
)

// 撤回申请（主播响应前可用）
coGuestStore.cancelApplication(
    completion: ((Result<Void, CoGuestError>) -> Void)?
)

// ── 主播端 ─────────────────────────────────────────────────────
// 同意连麦申请
coGuestStore.acceptApplication(
    userID: String,
    completion: ((Result<Void, CoGuestError>) -> Void)?
)

// 拒绝连麦申请
coGuestStore.rejectApplication(
    userID: String,
    completion: ((Result<Void, CoGuestError>) -> Void)?
)

// ── 断开连麦（主播/观众均可调用）──────────────────────────────
coGuestStore.disConnect(
    completion: ((Result<Void, CoGuestError>) -> Void)?
)

// ── 事件订阅 ───────────────────────────────────────────────────
coGuestStore.hostEventPublisher   // AnyPublisher<HostEvent, Never>
coGuestStore.guestEventPublisher  // AnyPublisher<GuestEvent, Never>
```

## 代码示例

### 观众端：申请 → 等待 → 开设备 → 连麦 → 断开

```swift
import AtomicXCore
import Combine

final class AudienceCoGuestViewModel: ObservableObject {

    // MARK: 状态

    enum CoGuestStatus {
        case idle           // 未连麦
        case applying       // 申请中
        case connected      // 连麦中
    }

    @Published var status: CoGuestStatus = .idle
    @Published var errorMessage: String?

    private let coGuestStore: CoGuestStore
    private var cancellables = Set<AnyCancellable>()
    private let applyTimeout: Double = 30

    init(liveID: String) {
        self.coGuestStore = CoGuestStore.create(liveID: liveID)
        observeGuestEvents()
    }

    // MARK: - 观众端事件订阅

    private func observeGuestEvents() {
        coGuestStore.guestEventPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] event in
                guard let self else { return }
                switch event {
                case .onGuestApplicationResponded(let response):
                    if response.isAccepted {
                        // ✅ 申请通过，立即开启设备
                        self.openDevicesAfterAccepted()
                    } else {
                        // 申请被拒绝
                        self.status = .idle
                        self.errorMessage = "连麦申请被主播拒绝"
                    }
                case .onCoGuestDisconnected:
                    // 被主播断开或自己断开
                    self.closeDevicesAfterDisconnect()
                    self.status = .idle
                default:
                    break
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - 申请连麦

    func applyForSeat() {
        guard status == .idle else { return }
        status = .applying

        coGuestStore.applyForSeat(
            timeout: applyTimeout,
            extraInfo: nil
        ) { [weak self] result in
            guard let self else { return }
            DispatchQueue.main.async {
                switch result {
                case .success:
                    // 申请发送成功，等待主播响应（通过 guestEventPublisher 回调）
                    print("[CoGuest] 申请已发送，等待主播响应...")
                case .failure(let error):
                    // 超时或麦位已满
                    self.status = .idle
                    if error.code == -2340 {
                        self.errorMessage = "当前连麦人数已达上限，请稍后再试"
                    } else {
                        self.errorMessage = "申请超时，请重试"
                    }
                }
            }
        }
    }

    // MARK: - 取消申请

    func cancelApplication() {
        guard status == .applying else { return }
        coGuestStore.cancelApplication { [weak self] _ in
            DispatchQueue.main.async {
                self?.status = .idle
            }
        }
    }

    // MARK: - 申请通过后开设备

    private func openDevicesAfterAccepted() {
        // 先开麦克风
        DeviceStore.shared.openLocalMicrophone { [weak self] micResult in
            guard let self else { return }
            switch micResult {
            case .failure(let error):
                print("[CoGuest] 麦克风打开失败: \(error.code)")
                self.errorMessage = "麦克风打开失败，请检查权限"
                // 麦克风失败，断开连麦
                self.coGuestStore.disConnect(completion: nil)
                DispatchQueue.main.async { self.status = .idle }
            case .success:
                // 再开摄像头
                DeviceStore.shared.openLocalCamera(isFront: true) { cameraResult in
                    DispatchQueue.main.async {
                        switch cameraResult {
                        case .failure(let error):
                            print("[CoGuest] 摄像头打开失败: \(error.code)")
                            // 摄像头失败不影响音频连麦，仅记录日志
                        case .success:
                            print("[CoGuest] 设备就绪，连麦中")
                        }
                        self.status = .connected
                    }
                }
            }
        }
    }

    // MARK: - 主动断开连麦

    func disconnect() {
        guard status == .connected else { return }
        coGuestStore.disConnect { [weak self] _ in
            self?.closeDevicesAfterDisconnect()
            DispatchQueue.main.async { self?.status = .idle }
        }
    }

    // MARK: - 断开后关闭设备

    private func closeDevicesAfterDisconnect() {
        DeviceStore.shared.closeLocalCamera()
        DeviceStore.shared.closeLocalMicrophone()
        print("[CoGuest] 连麦已断开，设备已关闭")
    }
}
```

---

### 主播端：监听申请 → 同意 / 拒绝 → 管理连麦

```swift
import AtomicXCore
import Combine

final class HostCoGuestViewModel: ObservableObject {

    // MARK: 状态

    @Published var pendingApplicants: [SeatInfo] = []   // 待审批申请列表
    @Published var connectedGuests: [SeatInfo]  = []    // 当前连麦列表

    private let coGuestStore: CoGuestStore
    private var cancellables = Set<AnyCancellable>()

    init(liveID: String) {
        self.coGuestStore = CoGuestStore.create(liveID: liveID)
        observeHostEvents()
        observeState()
    }

    // MARK: - 主播端事件订阅

    private func observeHostEvents() {
        coGuestStore.hostEventPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] event in
                guard let self else { return }
                switch event {
                case .onGuestApplicationReceived(let seatInfo):
                    // 新收到观众申请，添加到待审批列表
                    if !self.pendingApplicants.contains(where: { $0.userID == seatInfo.userID }) {
                        self.pendingApplicants.append(seatInfo)
                    }
                case .onCoGuestDisconnected(let userID):
                    // 某观众断开连麦
                    self.connectedGuests.removeAll { $0.userID == userID }
                default:
                    break
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - 状态订阅（实时同步连麦列表）

    private func observeState() {
        coGuestStore.$state
            .map(\.connected)
            .receive(on: DispatchQueue.main)
            .assign(to: &$connectedGuests)
    }

    // MARK: - 同意申请

    func acceptApplication(userID: String) {
        coGuestStore.acceptApplication(userID: userID) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self?.pendingApplicants.removeAll { $0.userID == userID }
                    print("[Host] 已同意 \(userID) 的连麦申请")
                case .failure(let error):
                    print("[Host] 同意申请失败: \(error.message)")
                }
            }
        }
    }

    // MARK: - 拒绝申请

    func rejectApplication(userID: String) {
        coGuestStore.rejectApplication(userID: userID) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    self?.pendingApplicants.removeAll { $0.userID == userID }
                    print("[Host] 已拒绝 \(userID) 的连麦申请")
                case .failure(let error):
                    print("[Host] 拒绝申请失败: \(error.message)")
                }
            }
        }
    }

    // MARK: - 主播踢出已连麦观众

    func kickGuest(userID: String) {
        coGuestStore.disConnect { result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    print("[Host] 已断开 \(userID) 的连麦")
                case .failure(let error):
                    print("[Host] 断开失败: \(error.message)")
                }
            }
        }
    }
}
```

---

### 连麦视频渲染（VideoViewDelegate）

```swift
extension LiveRoomViewController: VideoViewDelegate {

    func createCoGuestView(seatInfo: SeatInfo, viewLayer: ViewLayer) -> UIView? {
        switch viewLayer {
        case .background:
            // 摄像头关闭时展示头像占位图
            let avatarView = AvatarPlaceholderView()
            avatarView.configure(
                name: seatInfo.userName,
                avatarURL: seatInfo.userAvatar
            )
            return avatarView

        case .foreground:
            // 始终可见的用户信息条（名称 + 麦克风状态）
            let infoBar = CoGuestInfoBarView()
            infoBar.configure(
                userName: seatInfo.userName,
                isMicOn: seatInfo.userMicrophoneStatus == .on,
                isCameraOn: seatInfo.userCameraStatus == .on
            )
            return infoBar
        }
    }
}
```

## 调用时序

```
【观众端】
用户点击"申请连麦"
        │
        ▼
coGuestStore.applyForSeat(timeout: 30, extraInfo: nil)
        │
        ├─ .failure(-2340) → 麦位满，提示用户
        ├─ .failure(timeout) → 超时，提示重试
        │
        └─ .success（申请发出，等待主播响应）
                │
                ▼（guestEventPublisher 回调）
        onGuestApplicationResponded
                │
                ├─ .rejected → 提示被拒，status = .idle
                │
                └─ .accepted
                        │
                        ▼
                openLocalMicrophone()
                        │
                        ├─ .failure → disConnect，提示权限问题
                        └─ .success
                                │
                                ▼
                        openLocalCamera(isFront: true)
                                │
                                └─ .success / .failure（摄像头失败不影响音频连麦）
                                        │
                                        ▼
                                status = .connected（连麦中）
                                        │
                        ┌───────────────┘
                        │ 用户点击"断开连麦"
                        ▼
                coGuestStore.disConnect()
                        │
                        └─ closeLocalCamera()
                           closeLocalMicrophone()
                           status = .idle

【主播端（并行）】
订阅 hostEventPublisher
        │
        ▼
收到 onGuestApplicationReceived(seatInfo)
        │
        ├─ 主播点击"同意" → acceptApplication(userID:)
        │       └─ 从 pendingApplicants 移除
        └─ 主播点击"拒绝" → rejectApplication(userID:)
                └─ 从 pendingApplicants 移除
```

## 平台特有注意事项

### 1. Combine cancellable 生命周期管理
`hostEventPublisher` 和 `guestEventPublisher` 是 Combine Publisher。订阅时返回的 `AnyCancellable` 必须存储到 ViewModel/ViewController 的属性中（如 `Set<AnyCancellable>`），否则订阅会立即被释放，导致主播收不到任何申请事件。

### 2. 连麦中 App 进入后台
iOS 系统进入后台时会挂起摄像头采集，但麦克风仍可持续（需在 `Info.plist` 开启 `audio` 后台模式）。连麦场景建议在 App 进入后台时关闭摄像头（`closeLocalCamera()`），避免观众看到定格画面。

### 3. 设备权限时序
调用 `openLocalCamera` / `openLocalMicrophone` 前必须确认系统权限已授予（参考 [live/device-control](live/device-control.md)）。若在 `accepted` 回调触发时权限尚未授权，会导致设备打开失败、连麦无画面无声音。建议在用户点击"申请连麦"按钮时预先请求权限，而非等到 `accepted` 回调后才请求。

### 4. `-2340` 麦位超限
错误码 `-2340` 由服务端返回，表示当前直播间连麦人数已达上限。此时应禁用"申请连麦"按钮，并订阅 `CoGuestState.connected` 列表变化：当连麦人数减少时，自动重新启用按钮。
