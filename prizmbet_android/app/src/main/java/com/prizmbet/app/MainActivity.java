package com.prizmbet.app;

import android.content.Intent;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;

/**
 * PrizmBet Android wrapper.
 *
 * WebView loads the PWA hosted on GitHub Pages.
 * Features: loading indicator, error screen with retry, domain allowlist,
 * external links open in browser, immersive fullscreen, back navigation.
 */
public class MainActivity extends AppCompatActivity {

    // ── Configuration ────────────────────────────────────────────────────────────
    private static final String SITE_URL = "https://minortermite.github.io/prizmbet-v2/";

    /** Domains allowed to load inside the WebView. Everything else opens externally. */
    private static final String[] ALLOWED_HOSTS = {
            "minortermite.github.io",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
    };

    // ── Views ────────────────────────────────────────────────────────────────────
    private WebView webView;
    private ProgressBar progressBar;
    private View errorView;

    private boolean hasError = false;

    // ── Lifecycle ────────────────────────────────────────────────────────────────

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Fullscreen immersive — hide status bar and navigation bar
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

        configureWebView();
        // Сбрасываем HTTP-кэш WebView при каждом холодном старте.
        // Это гарантирует, что старый SW-кэш или зависшие ресурсы не мешают загрузке.
        webView.clearCache(true);
        webView.loadUrl(SITE_URL);

        // Back button: navigate WebView history first, then exit
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

    // ── WebView setup ────────────────────────────────────────────────────────────

    private void configureWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // LOAD_NO_CACHE: всегда идём в сеть/ServiceWorker, игнорируем HTTP-кэш WebView.
        // CacheStorage ServiceWorker при этом работает нормально (это другой уровень).
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);

        // Убираем маркер "wv" из User-Agent — некоторые CDN/сервисы блокируют WebView UA.
        // Вместо "Mozilla/5.0 ... Chrome/XX.X (wv)" получается обычный Chrome UA.
        String ua = s.getUserAgentString();
        ua = ua.replace("; wv)", ")");
        s.setUserAgentString(ua);

        // WebViewClient — domain allowlist + error handling
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String host = request.getUrl().getHost();
                if (host != null && isAllowedHost(host)) {
                    return false; // load inside WebView
                }
                // External link — open in browser
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
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
                if (!hasError) {
                    showWebView();
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                // Only show error screen for main frame navigation failures
                if (request.isForMainFrame()) {
                    hasError = true;
                    showError(getString(R.string.error_no_connection));
                }
            }
        });

        // WebChromeClient — progress bar
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

    // ── Helpers ──────────────────────────────────────────────────────────────────

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
        if (!isOnline()) {
            showError(getString(R.string.error_no_connection));
            return;
        }
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
