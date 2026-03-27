---
id: live/anchor-room-config
platform: ios
---

# 直播间配置 — iOS 实现

## 前置条件

**依赖安装（Podfile）**
```ruby
pod 'AtomicXCore', '~> 4.0'
```

**前置状态**：
- `LoginStore.shared.isLogin == true`（须完成登录）
- 已有合法的 `liveID`（ASCII 字符，长度 ≤ 48 字节）
- 摄像头/麦克风设备已打开（`DeviceStore.shared.openLocalCamera` 成功）

## API 调用

```swift
// 构建直播间配置
var liveInfo = LiveInfo()
liveInfo.liveID       = "your-live-id"         // 必填
liveInfo.liveName     = "直播间名称"             // 选填，≤ 30 字节 UTF-8
liveInfo.coverURL     = "https://cdn.example.com/cover.jpg"  // 选填
liveInfo.seatTemplate = .videoDynamicGrid9Seats  // 必填
liveInfo.notice       = "欢迎来到我的直播间"      // 选填

// 创建直播间（传入配置）
LiveListStore.shared.createLive(liveInfo: liveInfo) { result in
    // result: Result<Void, LiveError>
}

// 开播后动态更新 MetaData（仅房主/管理员可调用）
LiveListStore.shared.updateLiveMetaData(
    liveID: liveID,
    metaData: ["category": "gaming", "activityId": "act_001"]
) { result in
    // result: Result<Void, LiveError>
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `liveInfo.liveID` | `String` | 直播间唯一 ID；须为 ASCII，长度 ≤ 48 字节 |
| `liveInfo.liveName` | `String` | 显示名称；UTF-8，长度 ≤ 30 字节 |
| `liveInfo.seatTemplate` | `SeatTemplate` | 连麦座位模板枚举 |
| `metaData` | `[String: String]` | 键值对扩展信息；最多 10 key，单值 ≤ 2 KB，总 ≤ 16 KB |

## 代码示例

```swift
import UIKit
import AtomicXCore

/// 主播直播间配置页面
final class AnchorRoomConfigViewController: UIViewController {

    // MARK: - Properties

    private let liveID: String
    private var liveName: String = ""
    private var coverURL: String = ""
    private var customMetaData: [String: String] = [:]

    // MARK: - UI

    private let nameTextField: UITextField = {
        let tf = UITextField()
        tf.placeholder = "输入直播间名称（最多10个汉字）"
        tf.borderStyle = .roundedRect
        tf.clearButtonMode = .whileEditing
        return tf
    }()

    private let coverURLTextField: UITextField = {
        let tf = UITextField()
        tf.placeholder = "封面图 URL（可选）"
        tf.borderStyle = .roundedRect
        tf.keyboardType = .URL
        tf.autocapitalizationType = .none
        return tf
    }()

    private lazy var startButton: UIButton = {
        let btn = UIButton(type: .system)
        btn.setTitle("开始直播", for: .normal)
        btn.backgroundColor = .systemRed
        btn.setTitleColor(.white, for: .normal)
        btn.layer.cornerRadius = 24
        btn.addTarget(self, action: #selector(startLiveTapped), for: .touchUpInside)
        return btn
    }()

    // MARK: - Init

    init(liveID: String) {
        self.liveID = liveID
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError() }

    // MARK: - Lifecycle

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "直播间配置"
        view.backgroundColor = .systemBackground
        setupLayout()
    }

    // MARK: - Layout

    private func setupLayout() {
        let stack = UIStackView(arrangedSubviews: [nameTextField, coverURLTextField, startButton])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24),
            startButton.heightAnchor.constraint(equalToConstant: 48)
        ])
    }

    // MARK: - Actions

    @objc private func startLiveTapped() {
        let name = nameTextField.text?.trimmingCharacters(in: .whitespaces) ?? ""

        // 客户端侧校验：liveName ≤ 30 字节 UTF-8
        if !name.isEmpty {
            let byteCount = name.utf8.count
            if byteCount > 30 {
                showAlert(title: "名称过长",
                          message: "直播间名称不可超过 30 字节（约 10 个汉字），当前 \(byteCount) 字节")
                return
            }
        }

        // 构建 LiveInfo
        var liveInfo = LiveInfo()
        liveInfo.liveID       = liveID
        liveInfo.liveName     = name.isEmpty ? "我的直播间" : name
        liveInfo.coverURL     = coverURLTextField.text ?? ""
        liveInfo.seatTemplate = .videoDynamicGrid9Seats

        // 附加自定义 MetaData（示例）
        if !customMetaData.isEmpty {
            liveInfo.metaData = buildValidatedMetaData(customMetaData)
        }

        createLive(with: liveInfo)
    }

    // MARK: - Create Live

    private func createLive(with liveInfo: LiveInfo) {
        startButton.isEnabled = false
        startButton.setTitle("开播中…", for: .normal)

        LiveListStore.shared.createLive(liveInfo: liveInfo) { [weak self] result in
            guard let self else { return }
            DispatchQueue.main.async {
                self.startButton.isEnabled = true
                self.startButton.setTitle("开始直播", for: .normal)

                switch result {
                case .success:
                    print("[RoomConfig] 直播间创建成功, liveID: \(liveInfo.liveID)")
                    // 跳转到直播中页面
                    let liveVC = AnchorLiveViewController(liveID: liveInfo.liveID)
                    self.navigationController?.pushViewController(liveVC, animated: true)

                case .failure(let error):
                    self.handleCreateLiveError(error)
                }
            }
        }
    }

    // MARK: - MetaData Validation

    /// 校验并裁剪 MetaData，确保符合 10 key / 单值 ≤ 2KB / 总 ≤ 16KB 限制
    private func buildValidatedMetaData(_ raw: [String: String]) -> [String: String] {
        var validated: [String: String] = [:]
        let maxKeyCount = 10
        let maxValueBytes = 2 * 1024      // 2 KB
        let maxTotalBytes = 16 * 1024     // 16 KB
        var totalBytes = 0

        for (key, value) in raw.prefix(maxKeyCount) {
            let valueBytes = value.utf8.count
            guard valueBytes <= maxValueBytes else {
                print("[RoomConfig] MetaData key '\(key)' 值超过 2KB，已跳过")
                continue
            }
            guard totalBytes + valueBytes <= maxTotalBytes else {
                print("[RoomConfig] MetaData 总大小超过 16KB，已停止添加")
                break
            }
            validated[key] = value
            totalBytes += valueBytes
        }
        return validated
    }

    // MARK: - Error Handling

    private func handleCreateLiveError(_ error: LiveError) {
        let message: String
        switch error.code {
        case -2105: message = "直播间 ID 非法，请检查 liveID 格式（须为 ASCII，≤ 48 字节）"
        case -2107: message = "直播间名称非法，须为合法 UTF-8 字符串且 ≤ 30 字节"
        case -2108: message = "您已在其他直播间，请先退出当前直播再试"
        default:    message = "创建直播间失败（错误码 \(error.code)），请重试"
        }
        showAlert(title: "创建失败", message: message)
    }

    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "确定", style: .default))
        present(alert, animated: true)
    }
}
```

**动态更新 MetaData（开播后）**：
```swift
// 仅在确认当前用户为房主/管理员时调用
func updateMetaData(liveID: String, updates: [String: String]) {
    LiveListStore.shared.updateLiveMetaData(liveID: liveID, metaData: updates) { result in
        switch result {
        case .success:
            print("[RoomConfig] MetaData 更新成功")
        case .failure(let error):
            if error.code == -2300 {
                print("[RoomConfig] 权限不足，仅房主/管理员可更新 MetaData")
            } else {
                print("[RoomConfig] MetaData 更新失败, code: \(error.code)")
            }
        }
    }
}
```

## 调用时序

```
进入 AnchorRoomConfigViewController
        │
        ▼
用户输入直播间名称 / 封面 URL / 自定义配置
        │
        ▼
[点击「开始直播」]
        │
        ▼
客户端校验
├── liveName UTF-8 字节数 ≤ 30？
├── MetaData 单值 ≤ 2KB？
└── MetaData 总大小 ≤ 16KB？
        │
        ▼
构建 LiveInfo 结构体
（liveID + liveName + coverURL + seatTemplate）
        │
        ▼
LiveListStore.createLive(liveInfo:)
        │
        ├─ .failure(-2105) → liveID 格式错误
        ├─ .failure(-2107) → liveName 超长/非法
        ├─ .failure(-2108) → 已在其他房间
        │
        └─ .success
                │
                ▼
        跳转 AnchorLiveViewController
        （直播中页面，监听生命周期事件）
```

## 平台特有注意事项

### 1. liveName 字节数计算
Swift 中汉字使用 UTF-8 编码，每个汉字占 3 字节。判断是否超限：
```swift
let byteCount = liveName.utf8.count  // ✅ 正确做法
let charCount = liveName.count       // ❌ 字符数不等于字节数
```
30 字节 = 约 10 个汉字 = 30 个英文字母。

### 2. liveID 生成建议
建议在服务端生成 liveID 并下发，规则：
- 仅含字母、数字、下划线、连字符
- 长度控制在 8~32 字节
- 示例：`live_${userId}_${timestamp}` → `live_10001_1711593600`

### 3. coverURL 图片要求
- 建议宽高比 **9:16**（竖屏封面）
- 文件大小建议 ≤ 500 KB
- 须为公开可访问的 HTTPS URL
