<?php
/**
 * سازگاری درگاه با صفحه تسویه‌حساب بلوکی ووکامرس (Gutenberg Blocks).
 *
 * @package MyGateway
 */

namespace MyGateway\Operators\Woocommerce\Block;

use Automattic\WooCommerce\Blocks\Payments\Integrations\AbstractPaymentMethodType;
use MyGateway\Operators\Woocommerce\Operator;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * کلاس PaymentMethodBlock
 *
 * این کلاس متد پرداخت را به رجیستری بلوک‌های ووکامرس معرفی می‌کند تا
 * درگاه در قالب جدید Checkout (مبتنی بر React) نیز نمایش داده شود.
 */
final class PaymentMethodBlock extends AbstractPaymentMethodType {

	/**
	 * شناسه متد پرداخت (باید با شناسه درگاه یکی باشد).
	 *
	 * @var string
	 */
	protected $name = Operator::GATEWAY_ID;

	/**
	 * نمونه درگاه برای خواندن تنظیمات.
	 *
	 * @var Operator|null
	 */
	private $gateway = null;

	/**
	 * مقداردهی اولیه — خواندن تنظیمات ذخیره‌شده درگاه.
	 *
	 * @return void
	 */
	public function initialize() {
		$this->settings = get_option( 'woocommerce_' . Operator::GATEWAY_ID . '_settings', array() );
	}

	/**
	 * دریافت نمونه درگاه از رجیستری ووکامرس.
	 *
	 * @return Operator|null
	 */
	private function gateway(): ?Operator {
		if ( null !== $this->gateway ) {
			return $this->gateway;
		}

		if ( function_exists( 'WC' ) && WC()->payment_gateways() ) {
			$gateways = WC()->payment_gateways()->payment_gateways();

			if ( isset( $gateways[ Operator::GATEWAY_ID ] ) && $gateways[ Operator::GATEWAY_ID ] instanceof Operator ) {
				$this->gateway = $gateways[ Operator::GATEWAY_ID ];
			}
		}

		return $this->gateway;
	}

	/**
	 * آیا متد پرداخت فعال است؟
	 *
	 * @return bool
	 */
	public function is_active() {
		return 'yes' === $this->get_setting( 'enabled', 'no' );
	}

	/**
	 * ثبت و معرفی اسکریپت فرانت‌اند متد پرداخت.
	 *
	 * @return string[] هندل‌های اسکریپت.
	 */
	public function get_payment_method_script_handles() {
		$handle = 'my-gateway-blocks';

		$script_url  = MY_GATEWAY_PLUGIN_URL . 'src/Operators/Woocommerce/Block/assets/payment-method.js';
		$script_path = MY_GATEWAY_PLUGIN_DIR . 'src/Operators/Woocommerce/Block/assets/payment-method.js';

		wp_register_script(
			$handle,
			$script_url,
			array(
				'wc-blocks-registry',
				'wc-settings',
				'wp-element',
				'wp-html-entities',
				'wp-i18n',
			),
			file_exists( $script_path ) ? (string) filemtime( $script_path ) : MY_GATEWAY_VERSION,
			true
		);

		if ( function_exists( 'wp_set_script_translations' ) ) {
			wp_set_script_translations( $handle, 'my-gateway', MY_GATEWAY_PLUGIN_DIR . 'languages' );
		}

		return array( $handle );
	}

	/**
	 * داده‌هایی که به کامپوننت React فرانت‌اند تزریق می‌شوند.
	 *
	 * @return array<string,mixed>
	 */
	public function get_payment_method_data() {
		$gateway = $this->gateway();

		return array(
			'title'       => $this->get_setting( 'title', __( 'پرداخت امن آنلاین', 'my-gateway' ) ),
			'description' => $this->get_setting( 'description', '' ),
			'sandbox'     => 'yes' === $this->get_setting( 'sandbox', 'no' ),
			'icon'        => $gateway ? $gateway->icon : '',
			'supports'    => $gateway ? array_filter( $gateway->supports, array( $gateway, 'supports' ) ) : array( 'products' ),
		);
	}
}
