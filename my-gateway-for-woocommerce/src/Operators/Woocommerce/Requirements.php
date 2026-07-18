<?php
/**
 * بررسی پیش‌نیازهای اجرای افزونه.
 *
 * @package MyGateway
 */

namespace MyGateway\Operators\Woocommerce;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس Requirements
 *
 * قبل از اتصال درگاه به ووکامرس، برقراری همه پیش‌نیازها بررسی می‌شود:
 *  - نسخه PHP
 *  - نصب و فعال بودن ووکامرس (و حداقل نسخه آن)
 *  - سازگاری واحد پولی فروشگاه با درگاه‌های ریالی
 *  - وجود افزونه‌های ضروری PHP (curl / json)
 */
class Requirements {

	/**
	 * واحدهای پولی پشتیبانی‌شده توسط درگاه.
	 *
	 * @var string[]
	 */
	private const SUPPORTED_CURRENCIES = array( 'IRR', 'IRT', 'IRHR', 'IRHT', 'RIAL', 'TOMAN' );

	/**
	 * لیست خطاهای یافت‌شده.
	 *
	 * @var string[]
	 */
	private $errors = array();

	/**
	 * آیا بررسی انجام شده است؟
	 *
	 * @var bool
	 */
	private $checked = false;

	/**
	 * اجرای همه بررسی‌ها (فقط یک بار).
	 *
	 * @return void
	 */
	private function run_checks(): void {
		if ( $this->checked ) {
			return;
		}

		$this->checked = true;

		$this->check_php_version();
		$this->check_php_extensions();
		$this->check_woocommerce();
		$this->check_currency();
	}

	/**
	 * بررسی حداقل نسخه PHP.
	 *
	 * @return void
	 */
	private function check_php_version(): void {
		$min_php = defined( 'MY_GATEWAY_MIN_PHP' ) ? MY_GATEWAY_MIN_PHP : '7.4';

		if ( version_compare( PHP_VERSION, $min_php, '<' ) ) {
			$this->errors[] = sprintf(
				/* translators: 1: required PHP version, 2: current PHP version */
				__( 'درگاه My Gateway به PHP نسخه %1$s یا بالاتر نیاز دارد؛ نسخه فعلی سرور شما %2$s است.', 'my-gateway' ),
				$min_php,
				PHP_VERSION
			);
		}
	}

	/**
	 * بررسی افزونه‌های ضروری PHP.
	 *
	 * @return void
	 */
	private function check_php_extensions(): void {
		foreach ( array( 'curl', 'json' ) as $extension ) {
			if ( ! extension_loaded( $extension ) ) {
				$this->errors[] = sprintf(
					/* translators: %s: PHP extension name */
					__( 'افزونه PHP با نام %s روی سرور فعال نیست؛ برای کارکرد درگاه ضروری است.', 'my-gateway' ),
					$extension
				);
			}
		}
	}

	/**
	 * بررسی نصب و فعال بودن ووکامرس و حداقل نسخه آن.
	 *
	 * @return void
	 */
	private function check_woocommerce(): void {
		if ( ! class_exists( 'WooCommerce' ) || ! function_exists( 'WC' ) ) {
			$this->errors[] = __( 'برای استفاده از درگاه My Gateway باید افزونه ووکامرس نصب و فعال باشد.', 'my-gateway' );

			return;
		}

		$min_wc = defined( 'MY_GATEWAY_MIN_WC' ) ? MY_GATEWAY_MIN_WC : '5.0';

		if ( defined( 'WC_VERSION' ) && version_compare( WC_VERSION, $min_wc, '<' ) ) {
			$this->errors[] = sprintf(
				/* translators: 1: required WooCommerce version, 2: current WooCommerce version */
				__( 'درگاه My Gateway به ووکامرس نسخه %1$s یا بالاتر نیاز دارد؛ نسخه فعلی %2$s است.', 'my-gateway' ),
				$min_wc,
				WC_VERSION
			);
		}
	}

	/**
	 * بررسی همخوانی واحد پولی فروشگاه با درگاه ریالی.
	 *
	 * @return void
	 */
	private function check_currency(): void {
		// اگر ووکامرس فعال نیست، این بررسی بی‌معنی است.
		if ( ! function_exists( 'get_woocommerce_currency' ) ) {
			return;
		}

		$currency = strtoupper( get_woocommerce_currency() );

		if ( ! in_array( $currency, self::SUPPORTED_CURRENCIES, true ) ) {
			$this->errors[] = sprintf(
				/* translators: 1: current currency code, 2: supported currency codes */
				__( 'واحد پولی فعلی فروشگاه (%1$s) توسط درگاه My Gateway پشتیبانی نمی‌شود. واحدهای مجاز: %2$s', 'my-gateway' ),
				$currency,
				implode( '، ', self::SUPPORTED_CURRENCIES )
			);
		}
	}

	/**
	 * آیا همه پیش‌نیازها برقرارند؟
	 *
	 * @return bool
	 */
	public function are_satisfied(): bool {
		$this->run_checks();

		return empty( $this->errors );
	}

	/**
	 * دریافت لیست خطاها.
	 *
	 * @return string[]
	 */
	public function get_errors(): array {
		$this->run_checks();

		return $this->errors;
	}

	/**
	 * ثبت اعلان‌های مدیریتی برای نمایش خطاها به مدیر سایت.
	 *
	 * @return void
	 */
	public function register_admin_notices(): void {
		$errors = $this->get_errors();

		if ( empty( $errors ) || ! is_admin() ) {
			return;
		}

		add_action(
			'admin_notices',
			static function () use ( $errors ) {
				// فقط برای کاربرانی که توان مدیریت افزونه دارند.
				if ( ! current_user_can( 'activate_plugins' ) ) {
					return;
				}

				foreach ( $errors as $error ) {
					printf(
						'<div class="notice notice-error"><p><strong>My Gateway:</strong> %s</p></div>',
						esc_html( $error )
					);
				}
			}
		);
	}
}
