<?php
/**
 * سیستم لاگ هوشمند افزونه بر پایه Monolog با تاریخ شمسی.
 *
 * @package MyGateway
 */

namespace MyGateway;

use Monolog\Formatter\LineFormatter;
use Monolog\Handler\RotatingFileHandler;
use Monolog\Logger as MonologLogger;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس Logger
 *
 * یک لایه (Wrapper) امن و Singleton روی Monolog که:
 *  - لاگ‌ها را در پوشه‌ای محافظت‌شده (با .htaccess و نام هش‌شده) ذخیره می‌کند.
 *  - تاریخ هر رکورد را به‌صورت شمسی (جلالی) با کتابخانه jDateTime ثبت می‌کند.
 *  - در صورت هر خطای غیرمنتظره در فایل‌سیستم، به error_log پی‌اچ‌پی
 *    بازمی‌گردد تا هیچ لاگی از دست نرود.
 */
final class Logger {

	/**
	 * نام کانال لاگ.
	 */
	private const CHANNEL = 'my-gateway';

	/**
	 * حداکثر تعداد فایل‌های چرخشی (روزانه).
	 */
	private const MAX_FILES = 30;

	/**
	 * نمونه یکتای کلاس (Singleton).
	 *
	 * @var Logger|null
	 */
	private static $instance = null;

	/**
	 * نمونه Monolog.
	 *
	 * @var MonologLogger|null
	 */
	private $monolog = null;

	/**
	 * سازنده خصوصی برای الگوی Singleton.
	 */
	private function __construct() {
		$this->setup();
	}

	/**
	 * جلوگیری از clone شدن.
	 */
	private function __clone() {}

	/**
	 * دریافت نمونه یکتای Logger.
	 *
	 * @return Logger
	 */
	public static function instance(): Logger {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}

		return self::$instance;
	}

	/**
	 * راه‌اندازی Monolog، هندلر فایل و فرمت‌کننده شمسی.
	 *
	 * @return void
	 */
	private function setup(): void {
		try {
			$log_dir = $this->prepare_secure_log_dir();

			if ( null === $log_dir ) {
				return; // در متدهای ثبت، به error_log بازمی‌گردیم.
			}

			/*
			 * نام فایل با هش غیرقابل حدس ساخته می‌شود تا حتی در صورت
			 * از کار افتادن .htaccess (مثلاً روی Nginx) نتوان آدرس فایل
			 * لاگ را حدس زد.
			 */
			$hash     = substr( wp_hash( 'my-gateway-log-file' . ( defined( 'AUTH_KEY' ) ? AUTH_KEY : '' ) ), 0, 16 );
			$log_file = trailingslashit( $log_dir ) . 'my-gateway-' . $hash . '.log';

			$handler = new RotatingFileHandler( $log_file, self::MAX_FILES, MonologLogger::DEBUG );

			// فرمت هر خط لاگ؛ %extra.jalali_date% توسط پردازنده زیر پر می‌شود.
			$formatter = new LineFormatter(
				"[%extra.jalali_date%] %channel%.%level_name%: %message% %context%\n",
				null,
				true, // اجازه شکست خط در پیام.
				true  // نادیده گرفتن context خالی.
			);

			$handler->setFormatter( $formatter );

			$this->monolog = new MonologLogger( self::CHANNEL );
			$this->monolog->pushHandler( $handler );

			// پردازنده افزودن تاریخ شمسی و اطلاعات محیطی به هر رکورد.
			$this->monolog->pushProcessor(
				static function ( array $record ): array {
					$record['extra']['jalali_date'] = self::jalali_now();
					$record['extra']['ip']          = self::client_ip();
					$record['extra']['user_id']     = function_exists( 'get_current_user_id' ) ? get_current_user_id() : 0;

					return $record;
				}
			);
		} catch ( \Throwable $e ) {
			// عدم توقف سایت به‌خاطر خطای لاگر.
			$this->monolog = null;
			// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log
			error_log( '[my-gateway] Logger setup failed: ' . $e->getMessage() );
		}
	}

	/**
	 * ساخت پوشه امن لاگ در uploads به همراه فایل‌های محافظ.
	 *
	 * @return string|null مسیر پوشه یا null در صورت شکست.
	 */
	private function prepare_secure_log_dir(): ?string {
		$uploads = wp_upload_dir( null, false );

		if ( ! empty( $uploads['error'] ) ) {
			return null;
		}

		$log_dir = trailingslashit( $uploads['basedir'] ) . 'my-gateway-logs';

		if ( ! is_dir( $log_dir ) && ! wp_mkdir_p( $log_dir ) ) {
			return null;
		}

		// جلوگیری از دسترسی مستقیم وب به فایل‌های لاگ (Apache/LiteSpeed).
		$htaccess = trailingslashit( $log_dir ) . '.htaccess';
		if ( ! file_exists( $htaccess ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents
			file_put_contents( $htaccess, "Order deny,allow\nDeny from all\n<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n" );
		}

		// جلوگیری از فهرست شدن پوشه.
		$index = trailingslashit( $log_dir ) . 'index.html';
		if ( ! file_exists( $index ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents
			file_put_contents( $index, '' );
		}

		return $log_dir;
	}

	/**
	 * تاریخ و ساعت جاری به شمسی.
	 *
	 * @return string
	 */
	public static function jalali_now(): string {
		try {
			if ( class_exists( '\jDateTime' ) ) {
				// convert = false یعنی اعداد لاتین بمانند تا فایل لاگ ماشین‌خوان باشد.
				return \jDateTime::date( 'Y/m/d H:i:s', time(), false, true, 'Asia/Tehran' );
			}
		} catch ( \Throwable $e ) {
			// در صورت خطا، به تاریخ میلادی بازمی‌گردیم.
			unset( $e );
		}

		return gmdate( 'Y-m-d H:i:s' ) . ' UTC';
	}

	/**
	 * دریافت آی‌پی واقعی کاربر (با احتیاط نسبت به هدرهای جعلی).
	 *
	 * فقط REMOTE_ADDR منبع قابل اعتماد است؛ هدرهای Forwarded تنها ثبت
	 * می‌شوند و مبنای تصمیم امنیتی قرار نمی‌گیرند.
	 *
	 * @return string
	 */
	public static function client_ip(): string {
		$ip = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';

		return filter_var( $ip, FILTER_VALIDATE_IP ) ? $ip : 'unknown';
	}

	/**
	 * ثبت رکورد با سطح دلخواه.
	 *
	 * @param string $level   سطح لاگ (debug|info|warning|error|critical).
	 * @param string $message پیام.
	 * @param array  $context داده‌های زمینه‌ای.
	 * @return void
	 */
	public function log( string $level, string $message, array $context = array() ): void {
		try {
			if ( null !== $this->monolog ) {
				$this->monolog->log( $level, $message, $context );

				return;
			}
		} catch ( \Throwable $e ) {
			unset( $e );
		}

		// مسیر جایگزین: خروجی به error_log پی‌اچ‌پی.
		// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log
		error_log(
			sprintf(
				'[my-gateway][%s][%s] %s %s',
				self::jalali_now(),
				strtoupper( $level ),
				$message,
				wp_json_encode( $context, JSON_UNESCAPED_UNICODE )
			)
		);
	}

	/**
	 * ثبت لاگ سطح debug.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	public function debug( string $message, array $context = array() ): void {
		$this->log( 'debug', $message, $context );
	}

	/**
	 * ثبت لاگ سطح info.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	public function info( string $message, array $context = array() ): void {
		$this->log( 'info', $message, $context );
	}

	/**
	 * ثبت لاگ سطح warning.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	public function warning( string $message, array $context = array() ): void {
		$this->log( 'warning', $message, $context );
	}

	/**
	 * ثبت لاگ سطح error.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	public function error( string $message, array $context = array() ): void {
		$this->log( 'error', $message, $context );
	}

	/**
	 * ثبت لاگ سطح critical.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	public function critical( string $message, array $context = array() ): void {
		$this->log( 'critical', $message, $context );
	}
}
