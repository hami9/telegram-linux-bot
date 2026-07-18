<?php
/**
 * درایور نمونه اتصال به API درگاه پرداخت.
 *
 * @package MyGateway
 */

namespace MyGateway\Drivers;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس MyGatewayDriver
 *
 * پیاده‌سازی کامل قرارداد BaseDriver برای یک درگاه با API استاندارد
 * (توکن‌محور). برای اتصال به هر PSP واقعی (زرین‌پال، زیبال، آیدی‌پی،
 * درگاه مستقیم بانک و ...) کافی است آدرس Endpoint ها و نگاشت فیلدهای
 * پاسخ را مطابق مستندات همان درگاه تنظیم کنید — بقیه معماری بدون تغییر
 * کار می‌کند.
 */
class MyGatewayDriver extends BaseDriver {

	/**
	 * کد موفقیت استاندارد API درگاه.
	 */
	private const STATUS_SUCCESS = 100;

	/**
	 * کد «تراکنش قبلاً وریفای شده» — برای جلوگیری از خطای Double Verify.
	 */
	private const STATUS_ALREADY_VERIFIED = 101;

	/**
	 * آدرس پایه محیط عملیاتی.
	 */
	private const API_BASE_LIVE = 'https://api.mygateway.example/v1';

	/**
	 * آدرس پایه محیط آزمایشی (Sandbox).
	 */
	private const API_BASE_SANDBOX = 'https://sandbox.mygateway.example/v1';

	/**
	 * آدرس پایه صفحه پرداخت محیط عملیاتی.
	 */
	private const PAY_BASE_LIVE = 'https://pay.mygateway.example/start';

	/**
	 * آدرس پایه صفحه پرداخت محیط آزمایشی.
	 */
	private const PAY_BASE_SANDBOX = 'https://sandbox-pay.mygateway.example/start';

	/**
	 * نام یکتای درایور.
	 *
	 * @return string
	 */
	public function get_name(): string {
		return 'my-gateway-driver';
	}

	/**
	 * آیا حالت آزمایشی فعال است؟
	 *
	 * @return bool
	 */
	private function is_sandbox(): bool {
		return 'yes' === $this->config( 'sandbox', 'no' );
	}

	/**
	 * آدرس پایه API بر اساس محیط.
	 *
	 * @return string
	 */
	private function api_base(): string {
		return untrailingslashit(
			$this->is_sandbox()
				? (string) $this->config( 'api_base_sandbox', self::API_BASE_SANDBOX )
				: (string) $this->config( 'api_base_live', self::API_BASE_LIVE )
		);
	}

	/**
	 * هدرهای احراز هویت مشترک برای همه درخواست‌ها.
	 *
	 * @return array<string,string>
	 */
	private function auth_headers(): array {
		return array(
			'Authorization' => 'Bearer ' . (string) $this->config( 'api_key' ),
		);
	}

	/**
	 * ایجاد تراکنش و دریافت توکن پرداخت از بانک.
	 *
	 * @param array<string,mixed> $params پارامترهای تراکنش.
	 * @return array{success:bool,token:string,redirect_url:string,message:string,raw:array}
	 */
	public function request_payment( array $params ): array {
		$merchant_id = (string) $this->config( 'merchant_id' );
		$amount      = (int) ( $params['amount'] ?? 0 );

		$payload = array(
			'merchant_id'  => $merchant_id,
			'amount'       => $amount,
			'callback_url' => (string) ( $params['callback_url'] ?? '' ),
			'order_id'     => (string) ( $params['order_id'] ?? '' ),
			'description'  => (string) ( $params['description'] ?? '' ),
			'mobile'       => (string) ( $params['mobile'] ?? '' ),
			'email'        => (string) ( $params['email'] ?? '' ),
		);

		// امضای درخواست برای جلوگیری از دست‌کاری در مسیر (Anti-Tampering).
		$payload['signature'] = $this->generate_signature(
			array(
				'merchant_id' => $merchant_id,
				'amount'      => $amount,
				'order_id'    => $payload['order_id'],
			),
			(string) $this->config( 'api_key' )
		);

		$this->logger->info(
			'ارسال درخواست ایجاد تراکنش به بانک.',
			array(
				'order_id' => $payload['order_id'],
				'amount'   => $amount,
				'sandbox'  => $this->is_sandbox(),
			)
		);

		$response = $this->http_post( $this->api_base() . '/payment/request', $payload, $this->auth_headers() );

		if ( ! $response['success'] ) {
			return array(
				'success'      => false,
				'token'        => '',
				'redirect_url' => '',
				'message'      => $response['message'] ? $response['message'] : __( 'خطا در برقراری ارتباط با درگاه پرداخت.', 'my-gateway' ),
				'raw'          => $response['body'],
			);
		}

		$body   = $response['body'];
		$status = isset( $body['status'] ) ? (int) $body['status'] : -1;
		$token  = isset( $body['token'] ) ? (string) $body['token'] : '';

		if ( self::STATUS_SUCCESS !== $status || '' === $token || ! $this->is_valid_token_format( $token ) ) {
			$message = isset( $body['message'] ) ? (string) $body['message'] : $this->translate_status( $status );

			$this->logger->error(
				'بانک درخواست ایجاد تراکنش را نپذیرفت.',
				array(
					'order_id' => $payload['order_id'],
					'status'   => $status,
					'message'  => $message,
				)
			);

			return array(
				'success'      => false,
				'token'        => '',
				'redirect_url' => '',
				'message'      => $message,
				'raw'          => $body,
			);
		}

		$this->logger->info(
			'توکن پرداخت با موفقیت دریافت شد.',
			array(
				'order_id' => $payload['order_id'],
				'token'    => $token,
			)
		);

		return array(
			'success'      => true,
			'token'        => $token,
			'redirect_url' => $this->get_payment_url( $token ),
			'message'      => '',
			'raw'          => $body,
		);
	}

	/**
	 * آدرس صفحه پرداخت بانک.
	 *
	 * @param string $token توکن تراکنش.
	 * @return string
	 */
	public function get_payment_url( string $token ): string {
		$base = untrailingslashit(
			$this->is_sandbox()
				? (string) $this->config( 'pay_base_sandbox', self::PAY_BASE_SANDBOX )
				: (string) $this->config( 'pay_base_live', self::PAY_BASE_LIVE )
		);

		return $base . '/' . rawurlencode( $token );
	}

	/**
	 * صحت‌سنجی نهایی تراکنش پس از بازگشت از بانک.
	 *
	 * نکته امنیتی: مبلغ حتماً به همراه توکن ارسال و در سمت بانک تطبیق
	 * داده می‌شود تا حمله «تغییر مبلغ» ناکام بماند.
	 *
	 * @param array<string,mixed> $params شامل token و amount.
	 * @return array{success:bool,ref_id:string,card_number:string,status_code:string,message:string,raw:array}
	 */
	public function verify_payment( array $params ): array {
		$token  = (string) ( $params['token'] ?? '' );
		$amount = (int) ( $params['amount'] ?? 0 );

		if ( ! $this->is_valid_token_format( $token ) ) {
			return array(
				'success'     => false,
				'ref_id'      => '',
				'card_number' => '',
				'status_code' => 'invalid_token',
				'message'     => __( 'توکن تراکنش نامعتبر است.', 'my-gateway' ),
				'raw'         => array(),
			);
		}

		$payload = array(
			'merchant_id' => (string) $this->config( 'merchant_id' ),
			'token'       => $token,
			'amount'      => $amount,
		);

		$payload['signature'] = $this->generate_signature( $payload, (string) $this->config( 'api_key' ) );

		$this->logger->info( 'ارسال درخواست Verify به بانک.', array( 'token' => $token, 'amount' => $amount ) );

		$response = $this->http_post( $this->api_base() . '/payment/verify', $payload, $this->auth_headers() );

		$body   = $response['body'];
		$status = isset( $body['status'] ) ? (int) $body['status'] : -1;

		$is_success = $response['success'] && in_array( $status, array( self::STATUS_SUCCESS, self::STATUS_ALREADY_VERIFIED ), true );

		$result = array(
			'success'     => $is_success,
			'ref_id'      => isset( $body['ref_id'] ) ? (string) $body['ref_id'] : '',
			'card_number' => isset( $body['card_pan'] ) ? $this->mask_card( (string) $body['card_pan'] ) : '',
			'status_code' => (string) $status,
			'message'     => $is_success ? '' : ( isset( $body['message'] ) ? (string) $body['message'] : $this->translate_status( $status ) ),
			'raw'         => $body,
		);

		if ( $is_success ) {
			$this->logger->info(
				'تراکنش با موفقیت وریفای شد.',
				array(
					'token'  => $token,
					'ref_id' => $result['ref_id'],
					'status' => $status,
				)
			);
		} else {
			$this->logger->error(
				'وریفای تراکنش ناموفق بود.',
				array(
					'token'   => $token,
					'status'  => $status,
					'message' => $result['message'],
				)
			);
		}

		return $result;
	}

	/**
	 * استعلام مستقیم وضعیت تراکنش از بانک (پشتوانه Webhook).
	 *
	 * @param string              $token  توکن تراکنش.
	 * @param array<string,mixed> $params پارامترهای تکمیلی.
	 * @return array{success:bool,paid:bool,ref_id:string,status_code:string,message:string,raw:array}
	 */
	public function inquiry_transaction( string $token, array $params = array() ): array {
		if ( ! $this->is_valid_token_format( $token ) ) {
			return array(
				'success'     => false,
				'paid'        => false,
				'ref_id'      => '',
				'status_code' => 'invalid_token',
				'message'     => __( 'توکن تراکنش نامعتبر است.', 'my-gateway' ),
				'raw'         => array(),
			);
		}

		$payload = array(
			'merchant_id' => (string) $this->config( 'merchant_id' ),
			'token'       => $token,
		);

		$payload['signature'] = $this->generate_signature( $payload, (string) $this->config( 'api_key' ) );

		$this->logger->info( 'استعلام وضعیت تراکنش از بانک.', array( 'token' => $token ) );

		$response = $this->http_post( $this->api_base() . '/payment/inquiry', $payload, $this->auth_headers() );

		$body   = $response['body'];
		$status = isset( $body['status'] ) ? (int) $body['status'] : -1;
		$paid   = $response['success'] && in_array( $status, array( self::STATUS_SUCCESS, self::STATUS_ALREADY_VERIFIED ), true );

		/*
		 * اگر استعلام نشان دهد پرداخت انجام شده اما هنوز Verify نشده،
		 * همان‌جا Verify نهایی را نیز انجام می‌دهیم تا تراکنش در سمت
		 * بانک قطعی شود و وجه برگشت نخورد.
		 */
		if ( $paid && self::STATUS_SUCCESS === $status && ! empty( $params['amount'] ) ) {
			$verify = $this->verify_payment(
				array(
					'token'  => $token,
					'amount' => (int) $params['amount'],
				)
			);

			return array(
				'success'     => true,
				'paid'        => $verify['success'],
				'ref_id'      => $verify['ref_id'],
				'status_code' => $verify['status_code'],
				'message'     => $verify['message'],
				'raw'         => $verify['raw'],
			);
		}

		return array(
			'success'     => $response['success'],
			'paid'        => $paid,
			'ref_id'      => isset( $body['ref_id'] ) ? (string) $body['ref_id'] : '',
			'status_code' => (string) $status,
			'message'     => isset( $body['message'] ) ? (string) $body['message'] : $this->translate_status( $status ),
			'raw'         => $body,
		);
	}

	/**
	 * صحت‌سنجی امضای Webhook دریافتی از بانک (Anti-Spoofing).
	 *
	 * بانک باید هدر X-Gateway-Signature را برابر HMAC-SHA256 بدنه خام
	 * درخواست با کلید Webhook Secret ارسال کند.
	 *
	 * @param string $raw_body  بدنه خام درخواست.
	 * @param string $signature امضای دریافتی از هدر.
	 * @return bool
	 */
	public function verify_webhook_signature( string $raw_body, string $signature ): bool {
		$secret = (string) $this->config( 'webhook_secret' );

		if ( '' === $secret || '' === $signature ) {
			$this->logger->warning( 'امضای Webhook یا کلید محرمانه آن خالی است.' );

			return false;
		}

		$expected = hash_hmac( 'sha256', $raw_body, $secret );

		$is_valid = hash_equals( $expected, $signature );

		if ( ! $is_valid ) {
			$this->logger->error(
				'امضای Webhook نامعتبر است — احتمال درخواست جعلی.',
				array( 'ip' => \MyGateway\Logger::client_ip() )
			);
		}

		return $is_valid;
	}

	/**
	 * ماسک کردن شماره کارت برای ذخیره امن (فقط ۶ رقم اول و ۴ رقم آخر).
	 *
	 * @param string $card_pan شماره کارت.
	 * @return string
	 */
	private function mask_card( string $card_pan ): string {
		$digits = preg_replace( '/\D/', '', $card_pan );

		if ( strlen( $digits ) < 10 ) {
			return '';
		}

		return substr( $digits, 0, 6 ) . str_repeat( '*', strlen( $digits ) - 10 ) . substr( $digits, -4 );
	}

	/**
	 * ترجمه کدهای وضعیت بانک به پیام فارسی قابل نمایش.
	 *
	 * @param int $status کد وضعیت.
	 * @return string
	 */
	private function translate_status( int $status ): string {
		$map = array(
			100 => __( 'تراکنش با موفقیت انجام شد.', 'my-gateway' ),
			101 => __( 'تراکنش قبلاً تایید شده است.', 'my-gateway' ),
			-1  => __( 'پاسخ نامشخص از درگاه پرداخت.', 'my-gateway' ),
			-2  => __( 'پذیرنده نامعتبر است.', 'my-gateway' ),
			-3  => __( 'مبلغ تراکنش نامعتبر است.', 'my-gateway' ),
			-4  => __( 'تراکنش توسط کاربر لغو شد.', 'my-gateway' ),
			-5  => __( 'مهلت پرداخت تراکنش به پایان رسیده است.', 'my-gateway' ),
			-6  => __( 'تراکنش ناموفق بود یا توسط بانک برگشت داده شد.', 'my-gateway' ),
		);

		return isset( $map[ $status ] )
			? $map[ $status ]
			/* translators: %d: bank status code */
			: sprintf( __( 'خطای ناشناخته از سمت بانک (کد %d).', 'my-gateway' ), $status );
	}
}
