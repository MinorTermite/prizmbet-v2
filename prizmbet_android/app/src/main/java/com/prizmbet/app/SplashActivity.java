package com.prizmbet.app;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.splashscreen.SplashScreen;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;

import pl.droidsonroids.gif.GifDrawable;
import pl.droidsonroids.gif.GifImageView;

/**
 * Видео-заставка: воспроизводит prizmbet-logo.gif один раз,
 * затем плавно переходит в MainActivity.
 *
 * Фон и transition — единый #06060e на всём пути:
 *   OS splash (Theme.Prizmbet.Starting) → SplashActivity (#06060e + GIF)
 *   → fade → MainActivity (#06060e + WebView)  → контент
 * Пользователь не видит ни одной белой/чёрной вспышки.
 */
public class SplashActivity extends AppCompatActivity {

    /** Защита от двойного вызова launchMain (таймер + listener могут сработать вместе). */
    private final AtomicBoolean launched = new AtomicBoolean(false);

    /** Максимальное время показа заставки в мс (запасной таймер). */
    private static final int MAX_SPLASH_MS = 6000;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Устраняет чёрный экран пока Activity создаётся — OS уже показывает тему
        SplashScreen.installSplashScreen(this);
        super.onCreate(savedInstanceState);

        // Полноэкранный режим
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        enterImmersiveMode();

        // Фон окна = #06060e, совпадает с WebView → нет вспышки при переходе
        getWindow().setBackgroundDrawableResource(R.color.bg_primary);

        setContentView(R.layout.activity_splash);

        GifImageView gifView = findViewById(R.id.splashGif);

        try {
            GifDrawable drawable = new GifDrawable(getResources(), R.raw.prizmbet_logo);
            drawable.setLoopCount(1);  // Один раз — как в премиум-приложениях
            gifView.setImageDrawable(drawable);

            // Переходим когда GIF завершил воспроизведение
            drawable.addAnimationListener(loopNumber -> runOnUiThread(this::launchMain));

            // Запасной таймер: если GIF слишком длинный — не задерживаем пользователя
            gifView.postDelayed(this::launchMain, MAX_SPLASH_MS);

        } catch (IOException e) {
            // Если GIF не загрузился — сразу идём в приложение
            launchMain();
        }
    }

    /**
     * Плавный переход в MainActivity.
     * AtomicBoolean гарантирует одиночный вызов.
     */
    private void launchMain() {
        if (!launched.compareAndSet(false, true)) return;

        Intent intent = new Intent(this, MainActivity.class);

        // Прокидываем shortcut_action если запуск был через deep link
        String shortcut = getIntent().getStringExtra(MainActivity.EXTRA_SHORTCUT);
        if (shortcut != null) {
            intent.putExtra(MainActivity.EXTRA_SHORTCUT, shortcut);
        }

        startActivity(intent);

        // Плавный fade — фон одинаковый, переход незаметен
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
        finish();
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }
}
