<?php
/**
 * کلاس انتزاعی پایه برای تمام درایورهای درگاه پرداخت.
 *
 * @package MyGateway
 */

namespace MyGateway\Drivers;

use MyGateway\Logger;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس BaseDriver
 *
 * هر درگاه بانکی جدید فقط باید از این کلاس ارث‌بری کرده و متدهای
 * انتزاعی را پیاده‌سازی کند؛ بقیه زیرساخت (HTTP، امضا، لاگ، نرمال‌سازی
 * مبلغ) به‌صورت مشترک در همین‌جا فراهم شده است.
 */
abstract class BaseDriver {

	/**
	 * پیکربندی درایور (merchant_id، api_key و ...).
	 *
	 * @var array<string,mixed>
	 */
	protected $config = array();

	/**
	 * نمونه لاگر.
	 *
	 * @var Logger
	 */
	protected $logger;

	/**
	 * سازنده.
	 *
	 * @param array<string,mixed> $config پیکربندی درایور.
	 */
	public function __construct( array $config = array() ) {
		$this->config = $config;
		$this->logger = Logger::instance();
	}

	/*
	|--------------------------------------------------------------------------
	| قرارداد (Contract) درایورها — متدهای انتزاعی
	|--------------------------------------------------------------------------
	*/

	/**
	 * نام یکتای درایور.
	 *
	 * @return string
	 */
	abstract public function get_name(): string;

	/**
	 * ایجاد تراکنش جدید در سمت بانک و دریافت توکن پرداخت.
	 *
	 * @param array<string,mixed> $params شامل amount (ریال)، callback_url، order_id، mobile، email، description.
	 * @return array{success:bool,token:string,redirect_url:string,message:string,raw:array}
	 */
	abstract public function request_payment( array $params ): array;

	/**
	 * صحت‌سنجی (Verify) نهایی تراکنش پس از بازگشت از بانک.
	 *
	 * @param array<string,mixed> $params شامل token و amount (ریال).
	 * @return array{success:bool,ref_id:string,card_number:string,status_code:string,message:string,raw:array}
	 */
	abstract public function verify_payment( array $params ): array;

	/**
	 * استعلام مستقیم وضعیت تراکنش از بانک (پشتوانه مکانیزم Webhook).
	 *
	 * وقتی کاربر بعد از پرداخت صفحه را ببندد و به سایت برنگردد، از این
	 * متد برای تایید خودکار تراکنش استفاده می‌شود.
	 *
	 * @param string $token توکن تراکنش.
	 * @param array<string,mixed> $params پارامترهای تکمیلی (مثل amount).
	 * @return array{success:bool,paid:bool,ref_id:string,status_code:string,message:string,raw:array}
	 */
	abstract public function inquiry_transaction( string $token, array $params = array() ): array;

	/**
	 * آدرس صفحه پرداخت بانک برای هدایت مشتری.
	 *
	 * @param string $token توکن تراکنش.
	 * @return string
	 */
	abstract public function get_payment_url( string $token ): string;

	/*
	|--------------------------------------------------------------------------
	| ابزارهای مشترک و امنیتی
	|--------------------------------------------------------------------------
	*/

	/**
	 * خواندن یک کلید از پیکربندی.
	 *
	 * @param string $key     کلید.
	 * @param mixed  $default مقدار پیش‌فرض.
	 * @return mixed
	 */
	protected function config( string $key, $default = '' ) {
		return isset( $this->config[ $key ] ) ? $this->config[ $key ] : $default;
	}

	/**
	 * ارسال درخواست HTTP امن به API بانک (JSON).
	 *
	 * از wp_remote_post استفاده می‌شود تا با پروکسی/فایروال هاست‌ها
	 * سازگار باشد؛ تایید SSL هرگز غیرفعال نمی‌شود.
	 *
	 * @param string              $url     آدرس Endpoint.
	 * @param array<string,mixed> $body    بدنه درخواست.
	 * @param array<string,string> $headers هدرهای اضافه.
	 * @return array{success:bool,code:int,body:array,message:string}
	 */
	protected function http_post( string $url, array $body = array(), array $headers = array() ): array {
		$default_headers = array(
			'Content-Type' => 'application/json',
			'Accept'       => 'application/json',
			'User-Agent'   => 'MyGateway-WooCommerce/' . ( defined( 'MY_GATEWAY_VERSION' ) ? MY_GATEWAY_VERSION : '1.0.0' ),
		);

		$response = wp_remote_post(
			$url,
			array(
				'timeout'     => 30,
				'redirection' => 0,
				'sslverify'   => true,
				'headers'     => array_merge( $default_headers, $headers ),
				'body'        => wp_json_encode( $body, JSON_UNESCAPED_UNICODE ),
			)
		);

		if ( is_wp_error( $response ) ) {
			$this->logger->error(
				'خطای ارتباط با API بانک.',
				array(
					'driver' => $this->get_name(),
					'url'    => $url,
					'error'  => $response->get_error_message(),
				)
			);

			return array(
				'success' => false,
				'code'    => 0,
				'body'    => array(),
				'message' => $response->get_error_message(),
			);
		}

		$code     = (int) wp_remote_retrieve_response_code( $response );
		$raw_body = (string) wp_remote_retrieve_body( $response );
		$decoded  = json_decode( $raw_body, true );

		if ( ! is_array( $decoded ) ) {
			$this->logger->error(
				'پاسخ غیر JSON از API بانک دریافت شد.',
				array(
					'driver' => $this->get_name(),
					'url'    => $url,
					'code'   => $code,
					'body'   => mb_substr( $raw_body, 0, 500 ),
				)
			);

			return array(
				'success' => false,
				'code'    => $code,
				'body'    => array(),
				'message' => __( 'پاسخ نامعتبر از سرور بانک دریافت شد.', 'my-gateway' ),
			);
		}

		$this->logger->debug(
			'پاسخ API بانک دریافت شد.',
			array(
				'driver' => $this->get_name(),
				'url'    => $url,
				'code'   => $code,
			)
		);

		return array(
			'success' => $code >= 200 && $code < 300,
			'code'    => $code,
			'body'    => $decoded,
			'message' => '',
		);
	}

	/**
	 * ساخت امضای HMAC-SHA256 برای داده‌ها (Anti-Spoofing).
	 *
	 * کلیدها قبل از امضا مرتب می‌شوند تا امضا مستقل از ترتیب فیلدها باشد.
	 *
	 * @param array<string,mixed> $data   داده‌ها.
	 * @param string              $secret کلید محرمانه.
	 * @return string
	 */
	public function generate_signature( array $data, string $secret ): string {
		ksort( $data );

		return hash_hmac( 'sha256', wp_json_encode( $data, JSON_UNESCAPED_UNICODE ), $secret );
	}

	/**
	 * بررسی امضای دریافتی با مقایسه زمان-ثابت (در برابر Timing Attack).
	 *
	 * @param array<string,mixed> $data      داده‌ها.
	 * @param string              $signature امضای دریافتی.
	 * @param string              $secret    کلید محرمانه.
	 * @return bool
	 */
	public function verify_signature( array $data, string $signature, string $secret ): bool {
		if ( '' === $signature || '' === $secret ) {
			return false;
		}

		return hash_equals( $this->generate_signature( $data, $secret ), $signature );
	}

	/**
	 * صحت‌سنجی ساختاری توکن دریافتی از ورودی‌های خارجی.
	 *
	 * فقط کاراکترهای مجاز و طول منطقی پذیرفته می‌شود تا از تزریق
	 * داده‌های مخرب جلوگیری شود.
	 *
	 * @param string $token توکن.
	 * @return bool
	 */
	public function is_valid_token_format( string $token ): bool {
		return (bool) preg_match( '/^[A-Za-z0-9\-_\.]{8,128}$/', $token );
	}

	/**
	 * تبدیل مبلغ سفارش به ریال بر اساس واحد پولی فروشگاه.
	 *
	 * API اکثر بانک‌های ایرانی مبلغ را به ریال می‌پذیرند.
	 *
	 * @param float  $amount   مبلغ سفارش.
	 * @param string $currency کد واحد پولی ووکامرس.
	 * @return int مبلغ به ریال.
	 */
	public function normalize_amount_to_rial( float $amount, string $currency ): int {
		switch ( strtoupper( $currency ) ) {
			case 'IRT': // تومان.
			case 'TOMAN':
				$amount *= 10;
				break;
			case 'IRHT': // هزار تومان.
				$amount *= 10000;
				break;
			case 'IRHR': // هزار ریال.
				$amount *= 1000;
				break;
			case 'IRR': // ریال.
			case 'RIAL':
			default:
				break;
		}

		return (int) round( $amount );
	}
}
