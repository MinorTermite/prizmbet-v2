package com.prizmbet.app;

import android.content.Intent;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.MimeTypeMap;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.webkit.WebViewAssetLoader;

import java.io.IOException;
import java.io.InputStream;

/**
 * PrizmBet Android wrapper.
 * - WebViewAssetLoader: serves static assets from APK (instant load, no network needed)
 * - JSON match data always fetched from network (live data)
 * - App Shortcuts: Football / Esports / Refresh
 */
public class MainActivity extends AppCompatActivity {

    private static final String SITE_URL = "https://minortermite.github.io/prizmbet-v2/";
    public  static final String EXTRA_SHORTCUT = "shortcut_action";

    private static final String[] ALLOWED_HOSTS = {
            "minortermite.github.io",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
    };

    private WebView       webView;
    private ProgressBar   progressBar;
    private View          errorView;
    private WebViewAssetLoader assetLoader;

    /** Action requested via App Shortcut; applied once after first page load. */
    private String pendingShortcut = null;

    private boolean hasError = false;

    // ── Lifecycle ──────────────────────────────────────────────────────────────

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        enterImmersiveMode();

        setContentView(R.layout.activity_main);

        progressBar = findViewById(R.id.progressBar);
        errorView   = findViewById(R.id.errorView);
        webView     = findViewById(R.id.webView);

        Button retryBtn = findViewById(R.id.retryButton);
        retryBtn.setOnClickListener(v -> retry());

        buildAssetLoader();
        configureWebView();

        // Read App Shortcut action (if launched via shortcut)
        pendingShortcut = getIntent().getStringExtra(EXTRA_SHORTCUT);

        webView.clearCache(true);
        webView.loadUrl(SITE_URL);

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (errorView.getVisibility() == View.VISIBLE) {
                    finish();
                } else if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        });
    }

    /** Called when app is already running and a shortcut is tapped. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        String action = intent.getStringExtra(EXTRA_SHORTCUT);
        if (action != null) {
            pendingShortcut = action;
            applyShortcut(action);   // page is already loaded → apply immediately
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        enterImmersiveMode();
    }

    @Override
    protected void onPause() {
        webView.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.destroy();
        }
        super.onDestroy();
    }

    // ── Asset Loader ───────────────────────────────────────────────────────────

    /**
     * Builds a WebViewAssetLoader that intercepts requests to
     * https://minortermite.github.io/prizmbet-v2/* and serves them from
     * APK assets/prizmbet-v2/ — except live JSON data files which always
     * come from the network.
     */
    private void buildAssetLoader() {
        assetLoader = new WebViewAssetLoader.Builder()
                .setDomain("minortermite.github.io")
                .addPathHandler("/prizmbet-v2/", path -> {
                    // Live match data — always fetch from network
                    if (path.endsWith("matches.json") || path.endsWith("matches-today.json")) {
                        return null;
                    }
                    try {
                        InputStream is = getAssets().open("prizmbet-v2/" + path);
                        String ext = path.contains(".")
                                ? path.substring(path.lastIndexOf('.') + 1).toLowerCase()
                                : "";
                        String mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
                        if (mime == null) mime = "application/octet-stream";
                        // JS & CSS need charset for proper rendering
                        String charset = (mime.contains("javascript") || mime.contains("css")
                                || mime.contains("html") || mime.contains("json"))
                                ? "UTF-8" : null;
                        return new WebResourceResponse(mime, charset, is);
                    } catch (IOException e) {
                        return null; // Not in assets — fall through to network
                    }
                })
                .build();
    }

    // ── WebView Configuration ──────────────────────────────────────────────────

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT); // Используем стандартный кэш для стабильности
        s.setMediaPlaybackRequiresUserGesture(false);

        // Позволяем загрузку контента
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);

        // Remove "wv" WebView marker so site treats us like Chrome
        String ua = s.getUserAgentString();
        ua = ua.replace("; wv)", ")");
        s.setUserAgentString(ua);

        webView.setWebViewClient(new WebViewClient() {

            /** Intercept static assets → serve from APK. JSON data → network. */
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String host = request.getUrl().getHost();
                if (host != null && isAllowedHost(host)) {
                    return false;
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, request.getUrl());
                    startActivity(intent);
                } catch (Exception ignored) { }
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                hasError = false;
                progressBar.setVisibility(View.VISIBLE);

                // Внедряем заглушку для Notification API, чтобы JS не падал
                view.evaluateJavascript(
                    "(function() {" +
                    "  if (typeof Notification === 'undefined') {" +
                    "    window.Notification = {" +
                    "      permission: 'denied'," +
                    "      requestPermission: function() { return Promise.resolve('denied'); }," +
                    "      show: function() {}" +
                    "    };" +
                    "    console.log('Notification API polyfill injected');" +
                    "  }" +
                    "})();", null);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                if (!hasError) {
                    showWebView();
                }
                // Apply any pending shortcut action after page fully loads
                if (pendingShortcut != null) {
                    applyShortcut(pendingShortcut);
                    pendingShortcut = null;
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    hasError = true;
                    showError("Ошибка загрузки. Проверьте соединение.");
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress >= 100) {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });
    }

    // ── App Shortcuts ──────────────────────────────────────────────────────────

    /**
     * Applies the requested shortcut via JavaScript injection.
     * Runs after onPageFinished to ensure DOM is ready.
     */
    private void applyShortcut(String action) {
        String js;
        switch (action) {
            case "football":
                js = "(function(){ var t = document.querySelector('.tab[data-sport=\"football\"]'); if(t) t.click(); })();";
                break;
            case "esports":
                js = "(function(){ var t = document.querySelector('.tab[data-sport=\"esports\"]'); if(t) t.click(); })();";
                break;
            case "refresh":
                js = "(function(){ if(window.refreshData) window.refreshData(); })();";
                break;
            default:
                return;
        }
        webView.evaluateJavascript(js, null);
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private boolean isAllowedHost(String host) {
        for (String allowed : ALLOWED_HOSTS) {
            if (host.equals(allowed) || host.endsWith("." + allowed)) {
                return true;
            }
        }
        return false;
    }

    private void showError(String message) {
        webView.setVisibility(View.GONE);
        errorView.setVisibility(View.VISIBLE);
        progressBar.setVisibility(View.GONE);
        TextView errorMsg = findViewById(R.id.errorMessage);
        if (errorMsg != null) errorMsg.setText(message);
    }

    private void showWebView() {
        errorView.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
    }

    private void retry() {
        if (!isOnline()) return;
        showWebView();
        webView.loadUrl(SITE_URL);
    }

    private boolean isOnline() {
        ConnectivityManager cm = getSystemService(ConnectivityManager.class);
        if (cm == null) return false;
        Network net = cm.getActiveNetwork();
        if (net == null) return false;
        NetworkCapabilities caps = cm.getNetworkCapabilities(net);
        return caps != null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
