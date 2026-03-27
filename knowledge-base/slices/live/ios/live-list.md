---
id: live/live-list
platform: ios
---

# 直播列表 — iOS 实现

## 前置条件

**依赖安装（Podfile）**
```ruby
pod 'AtomicXCore', '~> 4.0'
```

**最低系统要求**：iOS 13.0+，Xcode 14.0+

**前置登录**：必须在 `LoginStore.shared.login` 成功回调后才可调用 `fetchLiveList`。

## API 调用

```swift
// 拉取直播列表（分页）
LiveListStore.shared.fetchLiveList(
    cursor: String,           // 首次传 ""，后续传上次返回的 cursor
    count: Int,               // 每页数量，推荐 20
    completion: ((Result<(list: [LiveInfo], cursor: String), Error>) -> Void)?
)

// 订阅状态快照（Combine）
LiveListStore.shared.liveListStatePublisher: AnyPublisher<LiveListState, Never>

// 订阅异步事件
LiveListStore.shared.liveListEventPublisher: AnyPublisher<LiveListEvent, Never>
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `cursor` | `String` | 分页游标；首次传 `""`，末页时返回 `""` |
| `count` | `Int` | 单次返回条数，建议 20，最大 50 |

**LiveInfo 关键字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `liveID` | `String` | 直播间唯一 ID |
| `categoryList` | `[String]` | 分类标签，用于客户端筛选 |
| `seatLayoutTemplateID` | `Int` | 1–199 语聊房；200–999 视频直播 |
| `metaData` | `[String: String]` | 自定义扩展数据 |

## 代码示例

### 1. 基础分页拉取 + 状态订阅

```swift
import AtomicXCore
import Combine

final class LiveListViewModel {

    // MARK: - Properties

    private(set) var liveList: [LiveInfo] = []
    private var nextCursor: String = ""
    private var isLoading = false
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Init

    init() {
        subscribeEvents()
    }

    // MARK: - 订阅直播事件

    private func subscribeEvents() {
        LiveListStore.shared.liveListEventPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] event in
                switch event {
                case .onLiveEnded(let liveID):
                    self?.removeLive(liveID: liveID)
                case .onKickedOutOfLive(let liveID):
                    self?.handleKickedOut(liveID: liveID)
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - 拉取列表（首次 or 下拉刷新）

    func fetchFirst(completion: @escaping ([LiveInfo]) -> Void) {
        nextCursor = ""
        liveList = []
        fetchNextPage(completion: completion)
    }

    // MARK: - 加载更多（上拉分页）

    func fetchMore(completion: @escaping ([LiveInfo]) -> Void) {
        guard !isLoading, !nextCursor.isEmpty else { return }
        fetchNextPage(completion: completion)
    }

    // MARK: - 分类筛选（客户端本地过滤）

    /// 按 seatLayoutTemplateID 范围过滤
    func filteredList(type: LiveRoomType) -> [LiveInfo] {
        switch type {
        case .voiceChat:
            return liveList.filter { (1...199).contains($0.seatLayoutTemplateID) }
        case .videoStream:
            return liveList.filter { (200...999).contains($0.seatLayoutTemplateID) }
        case .all:
            return liveList
        }
    }

    /// 按 categoryList 标签过滤
    func filteredList(category: String) -> [LiveInfo] {
        liveList.filter { $0.categoryList.contains(category) }
    }

    // MARK: - Private

    private func fetchNextPage(completion: @escaping ([LiveInfo]) -> Void) {
        guard !isLoading else { return }
        isLoading = true

        LiveListStore.shared.fetchLiveList(cursor: nextCursor, count: 20) { [weak self] result in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.isLoading = false
                switch result {
                case .success(let (list, cursor)):
                    self.liveList.append(contentsOf: list)
                    self.nextCursor = cursor  // cursor == "" 表示最后一页
                    completion(self.liveList)
                case .failure(let error):
                    print("[LiveList] fetchLiveList failed: \(error)")
                    completion(self.liveList)
                }
            }
        }
    }

    private func removeLive(liveID: String) {
        liveList.removeAll { $0.liveID == liveID }
    }

    private func handleKickedOut(liveID: String) {
        removeLive(liveID: liveID)
        // 通知 UI 展示被踢出提示
    }
}

enum LiveRoomType { case all, voiceChat, videoStream }
```

### 2. 滑动播放 — UICollectionView Cell 模式

```swift
import AtomicXCore
import UIKit

// MARK: - Cell（每个 Cell 持有独立 LiveCoreView）

final class LiveListCell: UICollectionViewCell {

    // ⚠️ 每个 Cell 创建一个独立实例，绝不共享
    private let liveCoreView = LiveCoreView()

    override init(frame: CGRect) {
        super.init(frame: frame)
        setupLiveCoreView()
    }

    required init?(coder: NSCoder) { fatalError() }

    private func setupLiveCoreView() {
        // 使用 .playView 模式（观众只看，不推流）
        let playView = liveCoreView.getView(type: .playView)
        contentView.addSubview(playView)
        playView.frame = contentView.bounds
        playView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
    }

    /// Cell 进入屏幕时开始播放
    func startPlay(liveID: String) {
        liveCoreView.setLiveID(liveID)
        // 预加载 / 进房由 WatchViewController 在 willDisplay 触发
    }

    /// Cell 离开屏幕时停止播放，释放解码资源
    func stopPlay() {
        liveCoreView.leaveLive { _ in }
    }
}

// MARK: - ViewController

final class LiveListViewController: UIViewController {

    private var viewModel = LiveListViewModel()
    private var liveList: [LiveInfo] = []

    private lazy var collectionView: UICollectionView = {
        let layout = UICollectionViewFlowLayout()
        layout.scrollDirection = .vertical
        layout.itemSize = UIScreen.main.bounds.size  // 全屏滑动
        layout.minimumLineSpacing = 0
        let cv = UICollectionView(frame: .zero, collectionViewLayout: layout)
        cv.isPagingEnabled = true
        cv.register(LiveListCell.self, forCellWithReuseIdentifier: "LiveListCell")
        cv.dataSource = self
        cv.delegate = self
        return cv
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.addSubview(collectionView)
        collectionView.frame = view.bounds
        loadData()
    }

    private func loadData() {
        viewModel.fetchFirst { [weak self] list in
            self?.liveList = list
            self?.collectionView.reloadData()
        }
    }
}

extension LiveListViewController: UICollectionViewDataSource {
    func collectionView(_ cv: UICollectionView, numberOfItemsInSection section: Int) -> Int {
        liveList.count
    }

    func collectionView(_ cv: UICollectionView,
                        cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
        let cell = cv.dequeueReusableCell(withReuseIdentifier: "LiveListCell",
                                          for: indexPath) as! LiveListCell
        return cell
    }
}

extension LiveListViewController: UICollectionViewDelegate {

    // Cell 即将显示：绑定 liveID，开始播放
    func collectionView(_ cv: UICollectionView,
                        willDisplay cell: UICollectionViewCell,
                        forItemAt indexPath: IndexPath) {
        guard let liveCell = cell as? LiveListCell else { return }
        liveCell.startPlay(liveID: liveList[indexPath.item].liveID)
    }

    // Cell 离开屏幕：停播，释放资源
    func collectionView(_ cv: UICollectionView,
                        didEndDisplaying cell: UICollectionViewCell,
                        forItemAt indexPath: IndexPath) {
        (cell as? LiveListCell)?.stopPlay()
    }

    // 滑到底部时加载更多
    func scrollViewDidScroll(_ scrollView: UIScrollView) {
        let offsetY = scrollView.contentOffset.y
        let contentHeight = scrollView.contentSize.height
        let threshold = contentHeight - scrollView.frame.height * 2
        if offsetY > threshold {
            viewModel.fetchMore { [weak self] list in
                guard let self = self else { return }
                let oldCount = self.liveList.count
                self.liveList = list
                let newIndexPaths = (oldCount..<list.count).map {
                    IndexPath(item: $0, section: 0)
                }
                self.collectionView.insertItems(at: newIndexPaths)
            }
        }
    }
}
```

## 调用时序

```
LoginStore.login 成功
    │
    ▼
LiveListStore.fetchLiveList(cursor: "", count: 20)
    │
    ├─ .failure → 检查登录态 / 网络
    │
    └─ .success(list, cursor)
            │
            ├─ 渲染列表（reloadData）
            ├─ 保存 nextCursor
            │
            ▼
        用户滑动 → willDisplay Cell
            │
            └─ cell.startPlay(liveID:)
                    │
                    └─ liveCoreView.setLiveID → liveCoreView.joinLive（观看）
                            │
                            Cell 离开 → cell.stopPlay()
                                    │
                                    └─ liveCoreView.leaveLive
```

## 平台特有注意事项

### 1. 内存管理：Cell 离屏必须停播

iOS UICollectionView 会缓存离屏 Cell，若不在 `didEndDisplaying` 中调用 `leaveLive`，旧 Cell 的 `LiveCoreView` 会继续解码、占用解码器硬件资源，在直播列表页快速滑动时极易触发内存警告甚至 OOM。

### 2. isPagingEnabled 与 minimumLineSpacing

全屏滑动时必须将 `minimumLineSpacing` 设为 `0`，否则 `isPagingEnabled` 的分页锚点计算会偏移，导致停留在两个 Cell 之间的缝隙处。

### 3. 首屏首个 Cell 的播放启动

`willDisplay` 在 `viewDidLoad` 后的第一次布局时即会触发，无需额外手动调用 `startPlay`；但如果列表数据是异步加载的（先 `reloadData` 后才有数据），需在 `reloadData` 完成后使用 `scrollToItem` 触发 `willDisplay`。

### 4. 后台切换处理

监听 `UIApplication.didEnterBackgroundNotification`，遍历所有可见 Cell 调用 `stopPlay()`；回到前台时（`willEnterForegroundNotification`）对当前可见 Cell 重新调用 `startPlay`，避免后台解码消耗 CPU 导致系统挂起 App。
