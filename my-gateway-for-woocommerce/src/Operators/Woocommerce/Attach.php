<?php
/**
 * اتصال و قلاب کردن افزونه به فیلترها و اکشن‌های ووکامرس.
 *
 * @package MyGateway
 */

namespace MyGateway\Operators\Woocommerce;

use MyGateway\Logger;
use MyGateway\Operators\Woocommerce\Block\PaymentMethodBlock;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس Attach
 *
 * تنها نقطه‌ای که هوک‌های وردپرس/ووکامرس در آن ثبت می‌شوند؛ بقیه
 * کلاس‌ها از چرخه هوک‌ها بی‌خبرند و مستقل قابل تست هستند.
 */
final class Attach {

	/**
	 * نمونه یکتای کلاس.
	 *
	 * @var Attach|null
	 */
	private static $instance = null;

	/**
	 * آیا هوک‌ها ثبت شده‌اند؟
	 *
	 * @var bool
	 */
	private $initialized = false;

	/**
	 * سازنده خصوصی (Singleton).
	 */
	private function __construct() {}

	/**
	 * جلوگیری از clone.
	 */
	private function __clone() {}

	/**
	 * دریافت نمونه یکتا.
	 *
	 * @return Attach
	 */
	public static function instance(): Attach {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}

		return self::$instance;
	}

	/**
	 * ثبت همه هوک‌های افزونه (فقط یک بار).
	 *
	 * @return void
	 */
	public function init(): void {
		if ( $this->initialized ) {
			return;
		}

		$this->initialized = true;

		// 1) معرفی درگاه به لیست درگاه‌های پرداخت ووکامرس.
		add_filter( 'woocommerce_payment_gateways', array( $this, 'register_gateway' ) );

		// 2) اعلام سازگاری با HPOS و صفحه تسویه‌حساب بلوکی (Cart & Checkout Blocks).
		add_action( 'before_woocommerce_init', array( $this, 'declare_wc_compatibilities' ) );

		// 3) ثبت متد پرداخت برای Checkout مبتنی بر Gutenberg Blocks.
		add_action( 'woocommerce_blocks_loaded', array( $this, 'register_block_support' ) );

		// 4) لینک «تنظیمات» در صفحه افزونه‌های وردپرس.
		add_filter( 'plugin_action_links_' . MY_GATEWAY_PLUGIN_BASENAME, array( $this, 'plugin_action_links' ) );

		/*
		 * 5) مسیرهای WC-API:
		 *    - بازگشت مشتری از بانک (Callback).
		 *    - سیگنال مستقیم بانک (Webhook) برای تایید خودکار تراکنش.
		 * این هوک‌ها مستقل از ساخته شدن نمونه درگاه ثبت می‌شوند تا در هر
		 * درخواستی (حتی بدون بارگذاری صفحه پرداخت) قابل اتکا باشند.
		 */
		add_action( 'woocommerce_api_' . Operator::CALLBACK_ROUTE, array( Operator::class, 'handle_callback_request' ) );
		add_action( 'woocommerce_api_' . Operator::WEBHOOK_ROUTE, array( Operator::class, 'handle_webhook_request' ) );

		Logger::instance()->debug( 'هوک‌های ووکامرس با موفقیت ثبت شدند.' );
	}

	/**
	 * افزودن کلاس درگاه به لیست درگاه‌های ووکامرس.
	 *
	 * @param string[] $gateways لیست کلاس‌های درگاه.
	 * @return string[]
	 */
	public function register_gateway( array $gateways ): array {
		$gateways[] = Operator::class;

		return $gateways;
	}

	/**
	 * اعلام سازگاری با قابلیت‌های جدید ووکامرس.
	 *
	 * - custom_order_tables (HPOS): جداول سفارش پرسرعت.
	 * - cart_checkout_blocks: صفحه تسویه‌حساب بلوکی.
	 *
	 * @return void
	 */
	public function declare_wc_compatibilities(): void {
		if ( ! class_exists( \Automattic\WooCommerce\Utilities\FeaturesUtil::class ) ) {
			return;
		}

		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility(
			'custom_order_tables',
			MY_GATEWAY_PLUGIN_FILE,
			true
		);

		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility(
			'cart_checkout_blocks',
			MY_GATEWAY_PLUGIN_FILE,
			true
		);
	}

	/**
	 * ثبت متد پرداخت در رجیستری بلوک‌های ووکامرس.
	 *
	 * @return void
	 */
	public function register_block_support(): void {
		if ( ! class_exists( \Automattic\WooCommerce\Blocks\Payments\Integrations\AbstractPaymentMethodType::class ) ) {
			return;
		}

		add_action(
			'woocommerce_blocks_payment_method_type_registration',
			static function ( \Automattic\WooCommerce\Blocks\Payments\PaymentMethodRegistry $registry ) {
				$registry->register( new PaymentMethodBlock() );

				Logger::instance()->debug( 'متد پرداخت در Checkout Blocks ثبت شد.' );
			}
		);
	}

	/**
	 * افزودن لینک تنظیمات به ردیف افزونه در صفحه افزونه‌ها.
	 *
	 * @param string[] $links لینک‌های فعلی.
	 * @return string[]
	 */
	public function plugin_action_links( array $links ): array {
		$settings_url = admin_url( 'admin.php?page=wc-settings&tab=checkout&section=' . Operator::GATEWAY_ID );

		array_unshift(
			$links,
			sprintf(
				'<a href="%s">%s</a>',
				esc_url( $settings_url ),
				esc_html__( 'تنظیمات درگاه', 'my-gateway' )
			)
		);

		return $links;
	}
}
