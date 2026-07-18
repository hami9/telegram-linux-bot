<?php
/**
 * راه‌اندازی اولیه افزونه و مدیریت هوک‌های سطح بالا.
 *
 * این فایل تنها نقطه ورود منطق افزونه است؛ کلاس‌ها طبق PSR-4 توسط
 * کامپوزر بارگذاری می‌شوند و این فایل صرفاً آن‌ها را به چرخه حیات
 * وردپرس متصل می‌کند.
 *
 * @package MyGateway
 */

use MyGateway\Logger;
use MyGateway\Operators\Woocommerce\Attach;
use MyGateway\Operators\Woocommerce\Requirements;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! function_exists( 'my_gateway_bootstrap' ) ) {
	/**
	 * بوت‌استرپ اصلی افزونه.
	 *
	 * ترتیب اجرا:
	 *  1. بارگذاری ترجمه‌ها (init).
	 *  2. بررسی پیش‌نیازها پس از بارگذاری همه افزونه‌ها (plugins_loaded).
	 *  3. در صورت برقراری پیش‌نیازها، اتصال درگاه به ووکامرس (Attach).
	 *
	 * @return void
	 */
	function my_gateway_bootstrap() {

		// بارگذاری فایل‌های ترجمه.
		add_action(
			'init',
			static function () {
				load_plugin_textdomain(
					'my-gateway',
					false,
					dirname( MY_GATEWAY_PLUGIN_BASENAME ) . '/languages'
				);
			}
		);

		// هوک فعال‌سازی: بررسی پیش‌نیازها قبل از فعال شدن افزونه.
		register_activation_hook( MY_GATEWAY_PLUGIN_FILE, 'my_gateway_on_activation' );

		// هوک غیرفعال‌سازی: پاک‌سازی موارد موقتی.
		register_deactivation_hook( MY_GATEWAY_PLUGIN_FILE, 'my_gateway_on_deactivation' );

		/*
		 * اتصال اصلی به ووکامرس.
		 * اولویت 11 تضمین می‌کند که ووکامرس (اولویت 10) قبل از ما
		 * بارگذاری شده باشد.
		 */
		add_action(
			'plugins_loaded',
			static function () {
				$requirements = new Requirements();

				if ( ! $requirements->are_satisfied() ) {
					// نمایش دلیل عدم فعال‌سازی به مدیر سایت.
					$requirements->register_admin_notices();

					Logger::instance()->warning(
						'پیش‌نیازهای افزونه برقرار نیست؛ درگاه بارگذاری نشد.',
						array( 'errors' => $requirements->get_errors() )
					);

					return;
				}

				// اتصال درگاه به فیلترها و اکشن‌های ووکامرس.
				Attach::instance()->init();
			},
			11
		);
	}
}

if ( ! function_exists( 'my_gateway_on_activation' ) ) {
	/**
	 * منطق زمان فعال‌سازی افزونه.
	 *
	 * در صورت نبود پیش‌نیازها، فعال‌سازی متوقف و پیام مناسب نمایش
	 * داده می‌شود تا کاربر با صفحه سفید مواجه نشود.
	 *
	 * @return void
	 */
	function my_gateway_on_activation() {
		$requirements = new Requirements();

		if ( ! $requirements->are_satisfied() ) {
			deactivate_plugins( MY_GATEWAY_PLUGIN_BASENAME );

			wp_die(
				implode( '<br>', array_map( 'esc_html', $requirements->get_errors() ) ),
				esc_html__( 'خطا در فعال‌سازی My Gateway', 'my-gateway' ),
				array( 'back_link' => true )
			);
		}

		// آماده‌سازی پوشه امن لاگ‌ها در همان ابتدا.
		Logger::instance()->info( 'افزونه My Gateway با موفقیت فعال شد.' );

		// ذخیره نسخه برای مهاجرت‌های آینده (Migration).
		update_option( 'my_gateway_version', MY_GATEWAY_VERSION );
	}
}

if ( ! function_exists( 'my_gateway_on_deactivation' ) ) {
	/**
	 * منطق زمان غیرفعال‌سازی افزونه.
	 *
	 * داده‌های حیاتی (تنظیمات و لاگ‌ها) حذف نمی‌شوند؛ فقط موارد موقت
	 * پاک‌سازی می‌شوند.
	 *
	 * @return void
	 */
	function my_gateway_on_deactivation() {
		Logger::instance()->info( 'افزونه My Gateway غیرفعال شد.' );

		// پاک‌سازی ترنزینت‌های (Transient) احتمالی افزونه.
		delete_transient( 'my_gateway_requirements_notice' );
	}
}
