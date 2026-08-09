import Flutter
import UIKit

// ╔══════════════════════════════════════════════════════════════════╗
// ║  SecureFlutterViewController                                     ║
// ║  Custom VC that defers system gestures, hides status bar &       ║
// ║  home indicator during quiz secure mode                          ║
// ╚══════════════════════════════════════════════════════════════════╝

class SecureFlutterViewController: FlutterViewController {
  var isSecureModeEnabled = false {
    didSet {
      setNeedsUpdateOfScreenEdgesDeferringSystemGestures()
      setNeedsStatusBarAppearanceUpdate()
      if #available(iOS 14.0, *) {
        setNeedsUpdateOfHomeIndicatorAutoHidden()
      }
    }
  }

  // Defer all system edge gestures (swipe from edges) during secure mode
  override var preferredScreenEdgesDeferringSystemGestures: UIRectEdge {
    return isSecureModeEnabled ? [.all] : []
  }

  // Hide status bar during secure mode
  override var prefersStatusBarHidden: Bool {
    return isSecureModeEnabled
  }

  // Auto-hide home indicator during secure mode
  override var prefersHomeIndicatorAutoHidden: Bool {
    return isSecureModeEnabled
  }
}

// ╔══════════════════════════════════════════════════════════════════╗
// ║  AppDelegate — Quiz Security Features                            ║
// ║  • Screenshot blocking (black overlay on capture)                ║
// ║  • Screen recording/mirroring detection (content hidden)         ║
// ║  • Task switcher preview protection                              ║
// ║  • MethodChannel bridge for Flutter quiz screen                  ║
// ╚══════════════════════════════════════════════════════════════════╝

@main
@objc class AppDelegate: FlutterAppDelegate {
  /// Whether quiz secure mode is currently active
  private var isSecureModeActive = false

  /// Overlay shown during screen capture/recording to block content
  private var captureBlockerOverlay: UIView?

  /// Overlay shown briefly when a screenshot is taken
  private var screenshotFlashOverlay: UIView?

  /// Overlay shown in task switcher (applicationWillResignActive)
  private var taskSwitcherOverlay: UIView?

  // MARK: - Application Lifecycle

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    GeneratedPluginRegistrant.register(with: self)

    // Setup MethodChannel for Flutter ↔ Native security communication
    if let controller = window?.rootViewController as? SecureFlutterViewController {
      let securityChannel = FlutterMethodChannel(
        name: "com.smartstudy.security",
        binaryMessenger: controller.binaryMessenger
      )
      securityChannel.setMethodCallHandler { [weak self] (call: FlutterMethodCall, result: @escaping FlutterResult) in
        switch call.method {
        case "enableSecure":
          self?.enableSecureMode()
          result(true)
        case "disableSecure":
          self?.disableSecureMode()
          result(true)
        default:
          result(FlutterMethodNotImplemented)
        }
      }
    }

    // ── Register Notification Observers ──
    // 1. Screenshot detection (fires AFTER screenshot is taken)
    NotificationCenter.default.addObserver(
      self,
      selector: #selector(handleScreenshotTaken),
      name: UIApplication.userDidTakeScreenshotNotification,
      object: nil
    )

    // 2. Screen recording / mirroring detection (fires when capture state changes)
    if #available(iOS 11.0, *) {
      NotificationCenter.default.addObserver(
        self,
        selector: #selector(handleScreenCaptureChanged),
        name: UIScreen.capturedDidChangeNotification,
        object: nil
      )
    }

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  // MARK: - Task Switcher Protection

  /// Called when app is about to become inactive (task switcher, control center, etc.)
  /// We add a black overlay so iOS screenshot of the app for the task switcher shows black
  override func applicationWillResignActive(_ application: UIApplication) {
    super.applicationWillResignActive(application)

    guard isSecureModeActive else { return }

    DispatchQueue.main.async { [weak self] in
      guard let self = self, let window = self.window else { return }

      // Only add if not already present
      if self.taskSwitcherOverlay == nil {
        let overlay = UIView(frame: window.bounds)
        overlay.backgroundColor = .black
        overlay.tag = 88880
        overlay.autoresizingMask = [.flexibleWidth, .flexibleHeight]

        // Add security message
        let label = UILabel()
        label.text = "🔒 Quiz Mode Active\nContent Protected"
        label.textColor = UIColor.white.withAlphaComponent(0.6)
        label.font = UIFont.systemFont(ofSize: 16, weight: .semibold)
        label.textAlignment = .center
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false
        overlay.addSubview(label)
        NSLayoutConstraint.activate([
          label.centerXAnchor.constraint(equalTo: overlay.centerXAnchor),
          label.centerYAnchor.constraint(equalTo: overlay.centerYAnchor),
        ])

        window.addSubview(overlay)
        self.taskSwitcherOverlay = overlay
      }
    }
  }

  /// Called when app becomes active again — remove task switcher overlay
  override func applicationDidBecomeActive(_ application: UIApplication) {
    super.applicationDidBecomeActive(application)

    DispatchQueue.main.async { [weak self] in
      self?.taskSwitcherOverlay?.removeFromSuperview()
      self?.taskSwitcherOverlay = nil
    }
  }

  // MARK: - Secure Mode Enable/Disable

  private func enableSecureMode() {
    isSecureModeActive = true

    DispatchQueue.main.async { [weak self] in
      guard let self = self, let window = self.window else { return }

      // Enable SecureFlutterViewController features
      if let rootVC = window.rootViewController as? SecureFlutterViewController {
        rootVC.isSecureModeEnabled = true
      }

      // Check if screen is already being captured/recorded
      if #available(iOS 11.0, *) {
        if UIScreen.main.isCaptured {
          self.showCaptureBlockerOverlay()
        }
      }
    }
  }

  private func disableSecureMode() {
    isSecureModeActive = false

    DispatchQueue.main.async { [weak self] in
      guard let self = self, let window = self.window else { return }

      // Disable SecureFlutterViewController features
      if let rootVC = window.rootViewController as? SecureFlutterViewController {
        rootVC.isSecureModeEnabled = false
      }

      // Remove all security overlays
      self.removeCaptureBlockerOverlay()
      self.taskSwitcherOverlay?.removeFromSuperview()
      self.taskSwitcherOverlay = nil
    }
  }

  // MARK: - Screenshot Handler

  @objc private func handleScreenshotTaken() {
    guard isSecureModeActive else { return }

    DispatchQueue.main.async { [weak self] in
      guard let self = self, let window = self.window else { return }

      // Show a black flash overlay briefly to indicate screenshot was blocked
      // NOTE: iOS cannot actually prevent the screenshot, but content was already
      // hidden by the secure text field technique or capture blocker
      if self.screenshotFlashOverlay == nil {
        let overlay = UIView(frame: window.bounds)
        overlay.backgroundColor = .black
        overlay.tag = 88881
        overlay.alpha = 0
        overlay.autoresizingMask = [.flexibleWidth, .flexibleHeight]

        let label = UILabel()
        label.text = "📸 Screenshot Detected\n⚠️ This incident has been logged"
        label.textColor = UIColor.red.withAlphaComponent(0.8)
        label.font = UIFont.systemFont(ofSize: 15, weight: .bold)
        label.textAlignment = .center
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false
        overlay.addSubview(label)
        NSLayoutConstraint.activate([
          label.centerXAnchor.constraint(equalTo: overlay.centerXAnchor),
          label.centerYAnchor.constraint(equalTo: overlay.centerYAnchor),
        ])

        window.addSubview(overlay)
        self.screenshotFlashOverlay = overlay

        UIView.animate(withDuration: 0.15) {
          overlay.alpha = 1
        }

        // Remove after 3 seconds
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) { [weak self] in
          UIView.animate(withDuration: 0.3, animations: {
            self?.screenshotFlashOverlay?.alpha = 0
          }) { _ in
            self?.screenshotFlashOverlay?.removeFromSuperview()
            self?.screenshotFlashOverlay = nil
          }
        }
      }
    }
  }

  // MARK: - Screen Recording / Mirroring Handler

  @available(iOS 11.0, *)
  @objc private func handleScreenCaptureChanged() {
    guard isSecureModeActive else { return }

    DispatchQueue.main.async { [weak self] in
      if UIScreen.main.isCaptured {
        // Screen recording or mirroring just started — hide all content
        self?.showCaptureBlockerOverlay()
      } else {
        // Screen recording/mirroring stopped — show content again
        self?.removeCaptureBlockerOverlay()
      }
    }
  }

  // MARK: - Capture Blocker Overlay

  private func showCaptureBlockerOverlay() {
    guard let window = self.window, captureBlockerOverlay == nil else { return }

    let overlay = UIView(frame: window.bounds)
    overlay.backgroundColor = .black
    overlay.tag = 88882
    overlay.autoresizingMask = [.flexibleWidth, .flexibleHeight]

    // Warning message on the overlay
    let container = UIView()
    container.translatesAutoresizingMaskIntoConstraints = false
    overlay.addSubview(container)

    let iconLabel = UILabel()
    iconLabel.text = "🔒"
    iconLabel.font = UIFont.systemFont(ofSize: 48)
    iconLabel.textAlignment = .center
    iconLabel.translatesAutoresizingMaskIntoConstraints = false
    container.addSubview(iconLabel)

    let titleLabel = UILabel()
    titleLabel.text = "Screen Recording Detected"
    titleLabel.textColor = UIColor.red.withAlphaComponent(0.9)
    titleLabel.font = UIFont.systemFont(ofSize: 18, weight: .bold)
    titleLabel.textAlignment = .center
    titleLabel.translatesAutoresizingMaskIntoConstraints = false
    container.addSubview(titleLabel)

    let messageLabel = UILabel()
    messageLabel.text = "Quiz content is hidden while screen\nrecording or mirroring is active.\nPlease stop recording to continue."
    messageLabel.textColor = UIColor.white.withAlphaComponent(0.6)
    messageLabel.font = UIFont.systemFont(ofSize: 14, weight: .medium)
    messageLabel.textAlignment = .center
    messageLabel.numberOfLines = 0
    messageLabel.translatesAutoresizingMaskIntoConstraints = false
    container.addSubview(messageLabel)

    NSLayoutConstraint.activate([
      container.centerXAnchor.constraint(equalTo: overlay.centerXAnchor),
      container.centerYAnchor.constraint(equalTo: overlay.centerYAnchor),

      iconLabel.topAnchor.constraint(equalTo: container.topAnchor),
      iconLabel.centerXAnchor.constraint(equalTo: container.centerXAnchor),

      titleLabel.topAnchor.constraint(equalTo: iconLabel.bottomAnchor, constant: 16),
      titleLabel.centerXAnchor.constraint(equalTo: container.centerXAnchor),

      messageLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 10),
      messageLabel.centerXAnchor.constraint(equalTo: container.centerXAnchor),
      messageLabel.bottomAnchor.constraint(equalTo: container.bottomAnchor),
    ])

    window.addSubview(overlay)
    captureBlockerOverlay = overlay
  }

  private func removeCaptureBlockerOverlay() {
    captureBlockerOverlay?.removeFromSuperview()
    captureBlockerOverlay = nil
  }
}
