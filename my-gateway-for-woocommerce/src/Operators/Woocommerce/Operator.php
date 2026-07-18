<?php
/**
 * کلاس اصلی درگاه پرداخت در ووکامرس.
 *
 * @package MyGateway
 */

namespace MyGateway\Operators\Woocommerce;

use MyGateway\Drivers\MyGatewayDriver;
use MyGateway\Logger;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس Operator
 *
 * ارث‌بری از WC_Payment_Gateway و مدیریت کامل چرخه پرداخت:
 *  - process_payment: ایجاد تراکنش و هدایت مشتری به بانک.
 *  - process_callback: بازگشت امن از بانک با لایه‌های ضدجعل.
 *  - process_webhook: تایید خودکار تراکنش با سیگنال مستقیم بانک.
 */
class Operator extends \WC_Payment_Gateway {

	/**
	 * شناسه یکتای درگاه در ووکامرس.
	 */
	public const GATEWAY_ID = 'my_gateway';

	/**
	 * مسیر WC-API برای بازگشت از بانک.
	 */
	public const CALLBACK_ROUTE = 'my_gateway_callback';

	/**
	 * مسیر WC-API برای وبهوک بانک.
	 */
	public const WEBHOOK_ROUTE = 'my_gateway_webhook';

	/**
	 * کلیدهای متا سفارش.
	 */
	private const META_TOKEN         = '_my_gateway_token';
	private const META_VERIFY_SECRET = '_my_gateway_verify_secret';
	private const META_AMOUNT_RIAL   = '_my_gateway_amount_rial';
	private const META_REF_ID        = '_my_gateway_ref_id';

	/**
	 * نمونه لاگر.
	 *
	 * @var Logger
	 */
	private $logger;

	/**
	 * نمونه درایور (Lazy).
	 *
	 * @var MyGatewayDriver|null
	 */
	private $driver = null;

	/**
	 * سازنده درگاه.
	 */
	public function __construct() {
		$this->id                 = self::GATEWAY_ID;
		$this->method_title       = __( 'درگاه پرداخت My Gateway', 'my-gateway' );
		$this->method_description = __( 'پرداخت امن آنلاین از طریق درگاه My Gateway با پشتیبانی از تایید خودکار تراکنش (Webhook).', 'my-gateway' );
		$this->has_fields         = false;
		$this->icon               = apply_filters( 'my_gateway_icon', MY_GATEWAY_PLUGIN_URL . 'assets/logo.png' );
		$this->supports           = array( 'products' );
		$this->logger             = Logger::instance();

		$this->init_form_fields();
		$this->init_settings();

		$this->title       = $this->get_option( 'title' );
		$this->description = $this->get_option( 'description' );

		// ذخیره تنظیمات در پیشخوان.
		add_action( 'woocommerce_update_options_payment_gateways_' . $this->id, array( $this, 'process_admin_options' ) );

		// نمایش فرم انتقال به بانک در صفحه رسید (حالت POST).
		add_action( 'woocommerce_receipt_' . $this->id, array( $this, 'receipt_page' ) );
	}

	/*
	|--------------------------------------------------------------------------
	| تنظیمات پیشخوان
	|--------------------------------------------------------------------------
	*/

	/**
	 * تعریف فیلدهای تنظیمات درگاه.
	 *
	 * @return void
	 */
	public function init_form_fields() {
		$this->form_fields = array(
			'enabled'          => array(
				'title'   => __( 'فعال‌سازی', 'my-gateway' ),
				'type'    => 'checkbox',
				'label'   => __( 'فعال کردن درگاه My Gateway', 'my-gateway' ),
				'default' => 'no',
			),
			'title'            => array(
				'title'       => __( 'عنوان درگاه', 'my-gateway' ),
				'type'        => 'text',
				'description' => __( 'عنوانی که مشتری در صفحه تسویه‌حساب می‌بیند.', 'my-gateway' ),
				'default'     => __( 'پرداخت امن آنلاین', 'my-gateway' ),
				'desc_tip'    => true,
			),
			'description'      => array(
				'title'       => __( 'توضیحات درگاه', 'my-gateway' ),
				'type'        => 'textarea',
				'description' => __( 'توضیحی که زیر عنوان درگاه در صفحه تسویه‌حساب نمایش داده می‌شود.', 'my-gateway' ),
				'default'     => __( 'پرداخت از طریق کلیه کارت‌های عضو شبکه شتاب', 'my-gateway' ),
				'desc_tip'    => true,
			),
			'api_settings'     => array(
				'title'       => __( 'تنظیمات اتصال به بانک', 'my-gateway' ),
				'type'        => 'title',
				'description' => '',
			),
			'merchant_id'      => array(
				'title'       => __( 'شناسه پذیرنده (Merchant ID)', 'my-gateway' ),
				'type'        => 'text',
				'description' => __( 'شناسه‌ای که هنگام ثبت‌نام از درگاه دریافت کرده‌اید.', 'my-gateway' ),
				'default'     => '',
				'desc_tip'    => true,
			),
			'api_key'          => array(
				'title'       => __( 'کلید API (محرمانه)', 'my-gateway' ),
				'type'        => 'password',
				'description' => __( 'کلید محرمانه امضای درخواست‌ها؛ هرگز آن را در اختیار دیگران قرار ندهید.', 'my-gateway' ),
				'default'     => '',
				'desc_tip'    => true,
			),
			'webhook_secret'   => array(
				'title'       => __( 'کلید محرمانه Webhook', 'my-gateway' ),
				'type'        => 'password',
				'description' => __( 'کلیدی که در پنل درگاه برای امضای Webhook تنظیم کرده‌اید. برای فعال شدن تایید خودکار تراکنش الزامی است.', 'my-gateway' ),
				'default'     => '',
				'desc_tip'    => true,
			),
			'sandbox'          => array(
				'title'       => __( 'حالت آزمایشی (Sandbox)', 'my-gateway' ),
				'type'        => 'checkbox',
				'label'       => __( 'فعال کردن محیط آزمایشی برای تست پرداخت بدون تراکنش واقعی', 'my-gateway' ),
				'default'     => 'no',
			),
			'redirect_method'  => array(
				'title'       => __( 'روش انتقال به بانک', 'my-gateway' ),
				'type'        => 'select',
				'description' => __( 'در حالت «فرم خودکار»، مشتری ابتدا صفحه رسید را می‌بیند و با فرم POST به بانک منتقل می‌شود.', 'my-gateway' ),
				'default'     => 'get',
				'desc_tip'    => true,
				'options'     => array(
					'get'  => __( 'انتقال مستقیم (Redirect)', 'my-gateway' ),
					'post' => __( 'فرم خودکار (POST)', 'my-gateway' ),
				),
			),
			'messages'         => array(
				'title'       => __( 'پیام‌ها', 'my-gateway' ),
				'type'        => 'title',
				'description' => __( 'می‌توانید از متغیر {ref_id} برای نمایش کد رهگیری استفاده کنید.', 'my-gateway' ),
			),
			'success_message'  => array(
				'title'   => __( 'پیام پرداخت موفق', 'my-gateway' ),
				'type'    => 'textarea',
				'default' => __( 'پرداخت شما با موفقیت انجام شد. کد رهگیری: {ref_id}', 'my-gateway' ),
			),
			'failed_message'   => array(
				'title'   => __( 'پیام پرداخت ناموفق', 'my-gateway' ),
				'type'    => 'textarea',
				'default' => __( 'متأسفانه پرداخت شما ناموفق بود. در صورت کسر مبلغ، طی ۷۲ ساعت به حساب شما باز می‌گردد.', 'my-gateway' ),
			),
			'advanced'         => array(
				'title'       => __( 'تنظیمات پیشرفته', 'my-gateway' ),
				'type'        => 'title',
				'description' => '',
			),
			'api_base_live'    => array(
				'title'       => __( 'آدرس API عملیاتی', 'my-gateway' ),
				'type'        => 'text',
				'description' => __( 'فقط در صورت تغییر آدرس رسمی درگاه مقداردهی کنید.', 'my-gateway' ),
				'default'     => '',
				'desc_tip'    => true,
			),
			'api_base_sandbox' => array(
				'title'       => __( 'آدرس API آزمایشی', 'my-gateway' ),
				'type'        => 'text',
				'default'     => '',
			),
			'debug'            => array(
				'title'   => __( 'لاگ اشکال‌زدایی', 'my-gateway' ),
				'type'    => 'checkbox',
				'label'   => __( 'ثبت جزئیات کامل تراکنش‌ها در فایل لاگ (با تاریخ شمسی)', 'my-gateway' ),
				'default' => 'yes',
			),
		);
	}

	/**
	 * صفحه تنظیمات مدیریت به همراه راهنمای آدرس‌های Callback و Webhook.
	 *
	 * @return void
	 */
	public function admin_options() {
		parent::admin_options();

		$callback_url = WC()->api_request_url( self::CALLBACK_ROUTE );
		$webhook_url  = WC()->api_request_url( self::WEBHOOK_ROUTE );

		printf(
			'<table class="form-table"><tr><th>%s</th><td><code>%s</code></td></tr><tr><th>%s</th><td><code>%s</code><p class="description">%s</p></td></tr></table>',
			esc_html__( 'آدرس بازگشت (Callback)', 'my-gateway' ),
			esc_html( $callback_url ),
			esc_html__( 'آدرس Webhook', 'my-gateway' ),
			esc_html( $webhook_url ),
			esc_html__( 'این آدرس را در پنل درگاه خود ثبت کنید تا در صورت بازنگشتن مشتری به سایت، تراکنش به‌صورت خودکار تایید شود.', 'my-gateway' )
		);
	}

	/*
	|--------------------------------------------------------------------------
	| درایور و ابزارهای داخلی
	|--------------------------------------------------------------------------
	*/

	/**
	 * ساخت (Lazy) نمونه درایور با تنظیمات جاری.
	 *
	 * @return MyGatewayDriver
	 */
	private function driver(): MyGatewayDriver {
		if ( null === $this->driver ) {
			$this->driver = new MyGatewayDriver(
				array(
					'merchant_id'      => $this->get_option( 'merchant_id' ),
					'api_key'          => $this->get_option( 'api_key' ),
					'webhook_secret'   => $this->get_option( 'webhook_secret' ),
					'sandbox'          => $this->get_option( 'sandbox', 'no' ),
					'api_base_live'    => $this->get_option( 'api_base_live' ) ? $this->get_option( 'api_base_live' ) : null,
					'api_base_sandbox' => $this->get_option( 'api_base_sandbox' ) ? $this->get_option( 'api_base_sandbox' ) : null,
				)
			);
		}

		return $this->driver;
	}

	/**
	 * لاگ اشکال‌زدایی فقط در صورت فعال بودن گزینه debug.
	 *
	 * @param string $message پیام.
	 * @param array  $context زمینه.
	 * @return void
	 */
	private function debug_log( string $message, array $context = array() ): void {
		if ( 'yes' === $this->get_option( 'debug', 'yes' ) ) {
			$this->logger->debug( $message, $context );
		}
	}

	/**
	 * نمایش فیلدهای درگاه در صفحه تسویه‌حساب (از طریق قالب قابل شخصی‌سازی).
	 *
	 * @return void
	 */
	public function payment_fields() {
		wc_get_template(
			'payment-form.php',
			array(
				'gateway'     => $this,
				'description' => $this->description,
				'is_sandbox'  => 'yes' === $this->get_option( 'sandbox', 'no' ),
			),
			'my-gateway/',
			MY_GATEWAY_PLUGIN_DIR . 'src/Operators/Woocommerce/templates/'
		);
	}

	/*
	|--------------------------------------------------------------------------
	| مرحله ۱: ایجاد تراکنش و هدایت به بانک
	|--------------------------------------------------------------------------
	*/

	/**
	 * پردازش پرداخت سفارش.
	 *
	 * @param int $order_id شناسه سفارش.
	 * @return array{result:string,redirect?:string}
	 */
	public function process_payment( $order_id ) {
		$order = wc_get_order( $order_id );

		if ( ! $order ) {
			wc_add_notice( __( 'سفارش یافت نشد.', 'my-gateway' ), 'error' );

			return array( 'result' => 'failure' );
		}

		$driver = $this->driver();
		$amount = $driver->normalize_amount_to_rial( (float) $order->get_total(), $order->get_currency() );

		/*
		 * توکن امنیتی یک‌بارمصرف (Anti-Spoofing):
		 * نسخه خام در آدرس بازگشت قرار می‌گیرد و فقط «هش» آن در دیتابیس
		 * ذخیره می‌شود؛ بنابراین حتی با دسترسی خواندنی به دیتابیس هم
		 * نمی‌توان آدرس بازگشت معتبر جعل کرد.
		 */
		try {
			$verify_secret = bin2hex( random_bytes( 20 ) );
		} catch ( \Exception $e ) {
			$verify_secret = wp_generate_password( 40, false, false );
		}

		$callback_url = add_query_arg(
			array(
				'wc_order' => $order->get_id(),
				'sig'      => $verify_secret,
			),
			WC()->api_request_url( self::CALLBACK_ROUTE )
		);

		$response = $driver->request_payment(
			array(
				'amount'       => $amount,
				'callback_url' => $callback_url,
				'order_id'     => (string) $order->get_id(),
				'mobile'       => $order->get_billing_phone(),
				'email'        => $order->get_billing_email(),
				'description'  => sprintf(
					/* translators: 1: order id, 2: site name */
					__( 'پرداخت سفارش شماره %1$s در %2$s', 'my-gateway' ),
					$order->get_order_number(),
					wp_specialchars_decode( get_bloginfo( 'name' ), ENT_QUOTES )
				),
			)
		);

		if ( ! $response['success'] ) {
			$this->logger->error(
				'ایجاد تراکنش ناموفق بود.',
				array(
					'order_id' => $order->get_id(),
					'message'  => $response['message'],
				)
			);

			$order->add_order_note(
				sprintf(
					/* translators: %s: error message */
					__( 'خطا در اتصال به درگاه My Gateway: %s', 'my-gateway' ),
					$response['message']
				)
			);

			wc_add_notice( $response['message'], 'error' );

			return array( 'result' => 'failure' );
		}

		// ذخیره اطلاعات تراکنش روی سفارش (سازگار با HPOS).
		$order->update_meta_data( self::META_TOKEN, $response['token'] );
		$order->update_meta_data( self::META_VERIFY_SECRET, wp_hash( $verify_secret ) );
		$order->update_meta_data( self::META_AMOUNT_RIAL, $amount );
		$order->update_status(
			'pending',
			sprintf(
				/* translators: %s: bank token */
				__( 'مشتری به درگاه بانک منتقل شد. توکن تراکنش: %s', 'my-gateway' ),
				$response['token']
			)
		);
		$order->save();

		$this->debug_log(
			'مشتری به درگاه منتقل شد.',
			array(
				'order_id' => $order->get_id(),
				'token'    => $response['token'],
				'amount'   => $amount,
			)
		);

		// حالت POST: ابتدا صفحه رسید، سپس فرم خودکار.
		if ( 'post' === $this->get_option( 'redirect_method', 'get' ) ) {
			return array(
				'result'   => 'success',
				'redirect' => $order->get_checkout_payment_url( true ),
			);
		}

		return array(
			'result'   => 'success',
			'redirect' => $response['redirect_url'],
		);
	}

	/**
	 * صفحه رسید: نمایش فرم خودکار انتقال به بانک (حالت POST).
	 *
	 * @param int $order_id شناسه سفارش.
	 * @return void
	 */
	public function receipt_page( $order_id ) {
		$order = wc_get_order( $order_id );

		if ( ! $order ) {
			return;
		}

		$token = (string) $order->get_meta( self::META_TOKEN );

		wc_get_template(
			'redirect-form.php',
			array(
				'gateway'     => $this,
				'order'       => $order,
				'token'       => $token,
				'payment_url' => $this->driver()->get_payment_url( $token ),
			),
			'my-gateway/',
			MY_GATEWAY_PLUGIN_DIR . 'src/Operators/Woocommerce/templates/'
		);
	}

	/*
	|--------------------------------------------------------------------------
	| مرحله ۲: بازگشت از بانک (Callback)
	|--------------------------------------------------------------------------
	*/

	/**
	 * نقطه ورود استاتیک مسیر بازگشت از بانک (WC-API).
	 *
	 * @return void
	 */
	public static function handle_callback_request(): void {
		( new self() )->process_callback();
	}

	/**
	 * پردازش امن بازگشت از بانک.
	 *
	 * @return void
	 */
	public function process_callback(): void {
		$this->send_security_headers();

		// دریافت و پاک‌سازی ورودی‌ها؛ اعتبارسنجی با توکن اختصاصی خودمان
		// انجام می‌شود، نه صرفاً پارامترهای بانک.
		// phpcs:disable WordPress.Security.NonceVerification.Recommended
		$order_id = isset( $_GET['wc_order'] ) ? absint( wp_unslash( $_GET['wc_order'] ) ) : 0;
		$secret   = isset( $_GET['sig'] ) ? sanitize_text_field( wp_unslash( $_GET['sig'] ) ) : '';
		// phpcs:enable WordPress.Security.NonceVerification.Recommended

		$order = $order_id ? wc_get_order( $order_id ) : false;

		// اعتبارسنجی اولیه: سفارش موجود و متعلق به همین درگاه باشد.
		if ( ! $order || $order->get_payment_method() !== $this->id ) {
			$this->logger->warning(
				'بازگشت از بانک با شناسه سفارش نامعتبر — درخواست مشکوک.',
				array(
					'order_id' => $order_id,
					'ip'       => Logger::client_ip(),
				)
			);

			$this->redirect_with_notice( wc_get_checkout_url(), __( 'سفارش موردنظر یافت نشد.', 'my-gateway' ), 'error' );
		}

		// لایه ضدجعل: مقایسه زمان-ثابت هشِ توکن بازگشت.
		$stored_secret_hash = (string) $order->get_meta( self::META_VERIFY_SECRET );

		if ( '' === $secret || '' === $stored_secret_hash || ! hash_equals( $stored_secret_hash, wp_hash( $secret ) ) ) {
			$this->logger->error(
				'توکن امنیتی بازگشت از بانک نامعتبر است — احتمال حمله جعل (Spoofing).',
				array(
					'order_id' => $order_id,
					'ip'       => Logger::client_ip(),
				)
			);

			$this->redirect_with_notice( wc_get_checkout_url(), __( 'درخواست نامعتبر است. لطفاً دوباره تلاش کنید.', 'my-gateway' ), 'error' );
		}

		// جلوگیری از پردازش دوباره: اگر قبلاً (مثلاً توسط Webhook) پرداخت شده است.
		if ( $order->is_paid() ) {
			$this->debug_log( 'سفارش قبلاً پرداخت شده بود؛ هدایت به صفحه تشکر.', array( 'order_id' => $order_id ) );

			wp_safe_redirect( $this->get_return_url( $order ) );
			exit;
		}

		// قفل هم‌زمانی: جلوگیری از رقابت Callback و Webhook روی یک سفارش.
		if ( ! $this->acquire_lock( $order->get_id() ) ) {
			// پردازش موازی در جریان است؛ مشتری را به صفحه سفارش می‌فرستیم.
			wp_safe_redirect( $order->get_checkout_order_received_url() );
			exit;
		}

		try {
			$token  = (string) $order->get_meta( self::META_TOKEN );
			$amount = (int) $order->get_meta( self::META_AMOUNT_RIAL );

			// کنترل تطابق مبلغ ذخیره‌شده با مبلغ فعلی سفارش (ضد دست‌کاری).
			$current_amount = $this->driver()->normalize_amount_to_rial( (float) $order->get_total(), $order->get_currency() );

			if ( $amount !== $current_amount ) {
				$this->logger->critical(
					'عدم تطابق مبلغ سفارش با مبلغ تراکنش!',
					array(
						'order_id'       => $order_id,
						'stored_amount'  => $amount,
						'current_amount' => $current_amount,
					)
				);

				$order->update_status( 'on-hold', __( 'عدم تطابق مبلغ تراکنش با سفارش؛ نیاز به بررسی دستی.', 'my-gateway' ) );

				$this->redirect_with_notice( wc_get_checkout_url(), __( 'خطای تطابق مبلغ؛ با پشتیبانی تماس بگیرید.', 'my-gateway' ), 'error' );
			}

			$verify = $this->driver()->verify_payment(
				array(
					'token'  => $token,
					'amount' => $amount,
				)
			);

			if ( $verify['success'] ) {
				$this->mark_order_paid( $order, $verify['ref_id'], $verify['card_number'], 'callback' );

				$this->redirect_with_notice(
					$this->get_return_url( $order ),
					str_replace( '{ref_id}', $verify['ref_id'], (string) $this->get_option( 'success_message' ) ),
					'success'
				);
			}

			// پرداخت ناموفق.
			$order->update_status(
				'failed',
				sprintf(
					/* translators: 1: status code, 2: message */
					__( 'پرداخت ناموفق (کد %1$s): %2$s', 'my-gateway' ),
					$verify['status_code'],
					$verify['message']
				)
			);

			$failed_message = (string) $this->get_option( 'failed_message' );

			$this->redirect_with_notice(
				wc_get_checkout_url(),
				'' !== $verify['message'] ? $verify['message'] : $failed_message,
				'error'
			);
		} finally {
			$this->release_lock( $order->get_id() );
		}
	}

	/*
	|--------------------------------------------------------------------------
	| مرحله ۳: Webhook — تایید خودکار بدون بازگشت مشتری
	|--------------------------------------------------------------------------
	*/

	/**
	 * نقطه ورود استاتیک مسیر Webhook (WC-API).
	 *
	 * @return void
	 */
	public static function handle_webhook_request(): void {
		( new self() )->process_webhook();
	}

	/**
	 * پردازش سیگنال مستقیم بانک.
	 *
	 * اگر مشتری بعد از پرداخت صفحه را ببندد و به سایت برنگردد، بانک این
	 * آدرس را صدا می‌زند؛ پس از صحت‌سنجی امضا، وضعیت تراکنش مستقیماً از
	 * بانک استعلام و در صورت پرداخت، سفارش به‌صورت خودکار تکمیل می‌شود.
	 *
	 * @return void
	 */
	public function process_webhook(): void {
		$this->send_security_headers();

		// فقط متد POST پذیرفته می‌شود.
		$method = isset( $_SERVER['REQUEST_METHOD'] ) ? strtoupper( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_METHOD'] ) ) ) : '';

		if ( 'POST' !== $method ) {
			$this->json_response( 405, array( 'error' => 'method_not_allowed' ) );
		}

		// بدنه خام برای صحت‌سنجی امضا لازم است.
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents
		$raw_body = (string) file_get_contents( 'php://input' );

		if ( '' === $raw_body || strlen( $raw_body ) > 10240 ) {
			$this->json_response( 400, array( 'error' => 'invalid_body' ) );
		}

		$signature = isset( $_SERVER['HTTP_X_GATEWAY_SIGNATURE'] )
			? sanitize_text_field( wp_unslash( $_SERVER['HTTP_X_GATEWAY_SIGNATURE'] ) )
			: '';

		// لایه ضدجعل: بدون امضای معتبر HMAC هیچ پردازشی انجام نمی‌شود.
		if ( ! $this->driver()->verify_webhook_signature( $raw_body, $signature ) ) {
			$this->json_response( 401, array( 'error' => 'invalid_signature' ) );
		}

		$payload = json_decode( $raw_body, true );

		if ( ! is_array( $payload ) ) {
			$this->json_response( 400, array( 'error' => 'invalid_json' ) );
		}

		$token    = isset( $payload['token'] ) ? sanitize_text_field( (string) $payload['token'] ) : '';
		$order_id = isset( $payload['order_id'] ) ? absint( $payload['order_id'] ) : 0;

		if ( '' === $token || ! $this->driver()->is_valid_token_format( $token ) ) {
			$this->json_response( 400, array( 'error' => 'invalid_token' ) );
		}

		// یافتن سفارش: اول با order_id، سپس جست‌وجو بر اساس توکن.
		$order = $order_id ? wc_get_order( $order_id ) : false;

		if ( ! $order ) {
			$order = $this->find_order_by_token( $token );
		}

		if ( ! $order || $order->get_payment_method() !== $this->id ) {
			$this->logger->warning( 'Webhook برای سفارش ناموجود دریافت شد.', array( 'order_id' => $order_id, 'token' => $token ) );

			$this->json_response( 404, array( 'error' => 'order_not_found' ) );
		}

		// توکن دریافتی باید دقیقاً با توکن ذخیره‌شده سفارش یکی باشد.
		$stored_token = (string) $order->get_meta( self::META_TOKEN );

		if ( '' === $stored_token || ! hash_equals( $stored_token, $token ) ) {
			$this->logger->error(
				'توکن Webhook با توکن سفارش مطابقت ندارد — احتمال درخواست جعلی.',
				array( 'order_id' => $order->get_id(), 'ip' => Logger::client_ip() )
			);

			$this->json_response( 401, array( 'error' => 'token_mismatch' ) );
		}

		// اگر قبلاً پرداخت شده، فقط تایید مجدد برمی‌گردانیم (Idempotent).
		if ( $order->is_paid() ) {
			$this->json_response(
				200,
				array(
					'status'   => 'already_processed',
					'order_id' => $order->get_id(),
				)
			);
		}

		if ( ! $this->acquire_lock( $order->get_id() ) ) {
			// پردازش موازی (مثلاً Callback) در جریان است.
			$this->json_response( 200, array( 'status' => 'processing' ) );
		}

		try {
			$amount = (int) $order->get_meta( self::META_AMOUNT_RIAL );

			// به payload بانک اعتماد نمی‌کنیم؛ وضعیت مستقیماً استعلام می‌شود.
			$inquiry = $this->driver()->inquiry_transaction( $token, array( 'amount' => $amount ) );

			if ( $inquiry['success'] && $inquiry['paid'] ) {
				$this->mark_order_paid( $order, $inquiry['ref_id'], '', 'webhook' );

				$this->json_response(
					200,
					array(
						'status'   => 'completed',
						'order_id' => $order->get_id(),
					)
				);
			}

			$this->debug_log(
				'استعلام Webhook انجام شد؛ تراکنش پرداخت‌شده نیست.',
				array(
					'order_id'    => $order->get_id(),
					'status_code' => $inquiry['status_code'],
				)
			);

			$this->json_response(
				200,
				array(
					'status'      => 'not_paid',
					'status_code' => $inquiry['status_code'],
				)
			);
		} finally {
			$this->release_lock( $order->get_id() );
		}
	}

	/*
	|--------------------------------------------------------------------------
	| ابزارهای امنیتی و کمکی
	|--------------------------------------------------------------------------
	*/

	/**
	 * ارسال هدرهای امنیتی برای مسیرهای Callback و Webhook.
	 *
	 * @return void
	 */
	private function send_security_headers(): void {
		if ( headers_sent() ) {
			return;
		}

		nocache_headers();
		header( 'X-Frame-Options: DENY' );
		header( 'X-Content-Type-Options: nosniff' );
		header( 'Referrer-Policy: no-referrer' );
		header( 'X-Robots-Tag: noindex, nofollow' );
	}

	/**
	 * تکمیل نهایی سفارش پرداخت‌شده (مشترک بین Callback و Webhook).
	 *
	 * @param \WC_Order $order       سفارش.
	 * @param string    $ref_id      کد رهگیری بانک.
	 * @param string    $card_number شماره کارت ماسک‌شده.
	 * @param string    $source      منبع تایید (callback|webhook).
	 * @return void
	 */
	private function mark_order_paid( \WC_Order $order, string $ref_id, string $card_number, string $source ): void {
		$order->update_meta_data( self::META_REF_ID, $ref_id );
		// توکن امنیتی یک‌بارمصرف باطل می‌شود تا بازپخش (Replay) ممکن نباشد.
		$order->delete_meta_data( self::META_VERIFY_SECRET );
		$order->payment_complete( $ref_id );

		$note = sprintf(
			/* translators: 1: jalali datetime, 2: ref id, 3: source */
			__( 'پرداخت در تاریخ %1$s تایید شد. کد رهگیری: %2$s (روش تایید: %3$s)', 'my-gateway' ),
			Logger::jalali_now(),
			$ref_id,
			'webhook' === $source ? __( 'وبهوک بانک', 'my-gateway' ) : __( 'بازگشت مشتری', 'my-gateway' )
		);

		if ( '' !== $card_number ) {
			$note .= ' — ' . sprintf(
				/* translators: %s: masked card number */
				__( 'شماره کارت: %s', 'my-gateway' ),
				$card_number
			);
		}

		$order->add_order_note( $note );
		$order->save();

		// سبد خرید فقط در جلسه فعال مشتری وجود دارد.
		if ( function_exists( 'WC' ) && WC()->cart instanceof \WC_Cart ) {
			WC()->cart->empty_cart();
		}

		$this->logger->info(
			'سفارش با موفقیت پرداخت و تکمیل شد.',
			array(
				'order_id' => $order->get_id(),
				'ref_id'   => $ref_id,
				'source'   => $source,
			)
		);
	}

	/**
	 * یافتن سفارش بر اساس توکن تراکنش (سازگار با HPOS).
	 *
	 * @param string $token توکن.
	 * @return \WC_Order|false
	 */
	private function find_order_by_token( string $token ) {
		$orders = wc_get_orders(
			array(
				'limit'      => 1,
				'meta_query' => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query
					array(
						'key'   => self::META_TOKEN,
						'value' => $token,
					),
				),
			)
		);

		return ! empty( $orders ) ? $orders[0] : false;
	}

	/**
	 * گرفتن قفل پردازش برای یک سفارش (ضد شرایط رقابتی Callback/Webhook).
	 *
	 * @param int $order_id شناسه سفارش.
	 * @return bool
	 */
	private function acquire_lock( int $order_id ): bool {
		$key = 'my_gateway_lock_' . $order_id;

		if ( false !== get_transient( $key ) ) {
			return false;
		}

		set_transient( $key, time(), 60 );

		return true;
	}

	/**
	 * آزادسازی قفل پردازش سفارش.
	 *
	 * @param int $order_id شناسه سفارش.
	 * @return void
	 */
	private function release_lock( int $order_id ): void {
		delete_transient( 'my_gateway_lock_' . $order_id );
	}

	/**
	 * ثبت اعلان برای مشتری و هدایت امن (فقط به آدرس‌های داخلی سایت).
	 *
	 * @param string $url    آدرس مقصد.
	 * @param string $notice متن اعلان.
	 * @param string $type   نوع اعلان (success|error|notice).
	 * @return void
	 */
	private function redirect_with_notice( string $url, string $notice, string $type = 'notice' ): void {
		if ( '' !== $notice && function_exists( 'wc_add_notice' ) && isset( WC()->session ) && WC()->session ) {
			wc_add_notice( $notice, $type );
		}

		wp_safe_redirect( $url );
		exit;
	}

	/**
	 * ارسال پاسخ JSON و پایان درخواست (مخصوص Webhook).
	 *
	 * @param int   $status_code کد وضعیت HTTP.
	 * @param array $data        داده پاسخ.
	 * @return void
	 */
	private function json_response( int $status_code, array $data ): void {
		wp_send_json( $data, $status_code );
	}
}
