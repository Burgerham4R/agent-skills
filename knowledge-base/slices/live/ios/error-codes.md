---
id: live/error-codes
platform: ios
---

# 错误码参考 — iOS 实现

## 前置条件

TRTC Live SDK 所有异步接口均通过 Swift `Result<T, Error>` 回调返回错误。错误对象实现了以下协议：

```swift
protocol TRTCError: Error {
    var code: Int { get }       // 错误码（负数：客户端；正数：服务端）
    var message: String { get } // 错误描述
}
```

## 错误回调捕获方式

所有 SDK 回调遵循统一的 `Result<T, Error>` 模式：

```swift
// 登录示例
LoginStore.shared.login(sdkAppID: appID, userID: userID, userSig: userSig) { result in
    switch result {
    case .success(let userInfo):
        // 处理成功
        break
    case .failure(let error):
        // 统一错误处理入口
        ErrorHandler.handle(error)
    }
}

// 设备操作示例
DeviceStore.shared.openLocalCamera(isFront: true) { result in
    switch result {
    case .success:
        break
    case .failure(let error):
        ErrorHandler.handle(error)
    }
}
```

## 错误码提取代码

```swift
import AtomicXCore

/// 统一错误处理器
final class ErrorHandler {

    // MARK: - 提取错误码

    /// 从任意 Error 中提取 TRTC 错误码
    static func extractCode(from error: Error) -> Int? {
        // 尝试转换为 TRTCError 协议
        if let trtcError = error as? TRTCError {
            return trtcError.code
        }
        // 通过 userInfo 提取（兼容 NSError 桥接）
        let nsError = error as NSError
        if let code = nsError.userInfo["code"] as? Int {
            return code
        }
        return nsError.code != 0 ? nsError.code : nil
    }

    /// 从任意 Error 中提取错误描述
    static func extractMessage(from error: Error) -> String {
        if let trtcError = error as? TRTCError {
            return trtcError.message
        }
        return error.localizedDescription
    }

    // MARK: - 分类处理

    /// 统一错误分发：根据错误码决定处理策略
    static func handle(_ error: Error,
                       context: String = #function,
                       retryHandler: (() -> Void)? = nil) {
        guard let code = extractCode(from: error) else {
            logUnknownError(error, context: context)
            return
        }

        let message = extractMessage(from: error)
        print("[ErrorHandler] [\(context)] code=\(code), msg=\(message)")

        switch code {
        // ── 通用错误 ──────────────────────────────────────────
        case -1000:
            showAlert(title: "配置错误", message: "SDKAppID 不合法，请检查控制台配置")
        case -1001:
            showAlert(title: "参数错误", message: "UserSig 已过期或参数不合法，请重新获取")
        case -1002:
            showAlert(title: "未登录", message: "请先完成登录后再进行操作")
        case -1003:
            guideToSystemPermissionSettings()
        case -2:
            // 限频：指数退避重试
            retryWithBackoff(handler: retryHandler)

        // ── 设备错误 ──────────────────────────────────────────
        case -1101:
            guideToSystemPermissionSettings(permissionType: .camera)
        case -1102:
            showAlert(title: "摄像头占用", message: "请关闭其他正在使用摄像头的应用后重试")
        case -1103:
            showAlert(title: "无摄像头", message: "当前设备不支持摄像头，请使用真机测试")
        case -1105:
            guideToSystemPermissionSettings(permissionType: .microphone)
        case -1106:
            showAlert(title: "麦克风占用", message: "请结束通话或关闭其他语音应用后重试")
        case -1100, -1104:
            showAlert(title: "设备错误", message: "设备打开失败（code: \(code)），请重启应用后重试")

        // ── 房间错误 ──────────────────────────────────────────
        case -2101:
            showAlert(title: "操作错误", message: "请先进入房间再执行此操作")
        case -2108:
            showAlert(title: "已在房间内", message: "您已在其他房间中，请先退出后再加入新房间")

        // ── 权限/信令错误 ─────────────────────────────────────
        case -2380:
            showAlert(title: "全员禁言", message: "当前房间已开启全员禁言，请等待房主解除")
        case -2381:
            showAlert(title: "被禁言", message: "您已被禁言，请联系房主申请解除")
        case -2361, -2371:
            showAlert(title: "需要申请", message: "请向房主或管理员申请开启麦克风/摄像头权限")

        // ── 服务端错误（可重试）──────────────────────────────
        case 100001:
            retryWithBackoff(handler: retryHandler)

        // ── 未知错误 ──────────────────────────────────────────
        default:
            logUnknownError(error, context: context)
            showAlert(title: "未知错误", message: "错误码：\(code)\n\(message)")
        }
    }

    // MARK: - 工具方法

    private static func showAlert(title: String, message: String) {
        DispatchQueue.main.async {
            guard let topVC = UIApplication.shared.topViewController else { return }
            let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "确定", style: .default))
            topVC.present(alert, animated: true)
        }
    }

    enum PermissionType { case camera, microphone }

    private static func guideToSystemPermissionSettings(permissionType: PermissionType? = nil) {
        let message: String
        switch permissionType {
        case .camera:
            message = "请前往「设置 > 隐私与安全 > 摄像头」开启权限"
        case .microphone:
            message = "请前往「设置 > 隐私与安全 > 麦克风」开启权限"
        case nil:
            message = "请前往系统设置开启所需权限"
        }
        DispatchQueue.main.async {
            guard let topVC = UIApplication.shared.topViewController else { return }
            let alert = UIAlertController(title: "权限不足", message: message, preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "去设置", style: .default) { _ in
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            })
            alert.addAction(UIAlertAction(title: "取消", style: .cancel))
            topVC.present(alert, animated: true)
        }
    }

    private static var retryCount = 0
    private static let maxRetries = 3

    private static func retryWithBackoff(handler: (() -> Void)?) {
        guard let handler = handler, retryCount < maxRetries else {
            retryCount = 0
            showAlert(title: "请求失败", message: "多次重试后仍然失败，请稍后再试")
            return
        }
        let delay = pow(2.0, Double(retryCount))
        retryCount += 1
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
            handler()
        }
    }

    private static func logUnknownError(_ error: Error, context: String) {
        // 上报到业务日志系统（替换为实际日志 SDK）
        print("[ErrorHandler] 未知错误 [\(context)]: \(error)")
    }
}

// MARK: - UIApplication 顶层 ViewController 扩展
extension UIApplication {
    var topViewController: UIViewController? {
        var topVC = connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap { $0.windows }
            .first { $0.isKeyWindow }?
            .rootViewController
        while let presented = topVC?.presentedViewController {
            topVC = presented
        }
        return topVC
    }
}
```

## iOS 特有：权限错误与系统权限对应

iOS 系统权限与 TRTC 错误码的对应关系：

| TRTC 错误码 | AVFoundation 权限状态 | 系统设置路径 | 处理方式 |
|------------|----------------------|-------------|---------|
| `-1101` | `AVAuthorizationStatus.denied` (摄像头) | 设置 > 隐私与安全 > 摄像头 | 弹窗引导跳转 `UIApplication.openSettingsURLString` |
| `-1105` | `AVAuthorizationStatus.denied` (麦克风) | 设置 > 隐私与安全 > 麦克风 | 弹窗引导跳转 `UIApplication.openSettingsURLString` |
| `-1003` | 系统级权限被拒 | 设置 > 隐私与安全 | 通用权限引导 |

**权限状态主动检测**（在调用 SDK 前预检）：

```swift
import AVFoundation

/// 在 openLocalCamera 前检测，避免因权限问题收到错误码后再处理
func checkAndRequestCameraPermission(completion: @escaping (Bool) -> Void) {
    let status = AVCaptureDevice.authorizationStatus(for: .video)
    switch status {
    case .authorized:
        completion(true)
    case .notDetermined:
        // 首次询问 — 系统弹窗只弹一次
        AVCaptureDevice.requestAccess(for: .video) { granted in
            DispatchQueue.main.async { completion(granted) }
        }
    case .denied, .restricted:
        // 已拒绝 — 引导前往系统设置（requestAccess 不再弹窗）
        DispatchQueue.main.async {
            ErrorHandler.guideToSystemPermissionSettings(permissionType: .camera)
            completion(false)
        }
    @unknown default:
        completion(false)
    }
}
```

**注意事项**：
- `AVCaptureDevice.requestAccess` 只触发**一次**系统弹窗。用户拒绝后，再次调用不会弹窗，需手动引导前往设置。
- iOS 模拟器不支持摄像头，`AVAuthorizationStatus` 始终返回 `.authorized` 但打开后会收到 `-1103`，请在真机上测试设备功能。
- 权限状态缓存在 App 沙盒中，卸载重装后会重置。测试时需注意。
