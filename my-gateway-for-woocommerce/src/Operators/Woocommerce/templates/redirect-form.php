<?php
/**
 * قالب فرم انتقال خودکار به درگاه بانک (حالت POST).
 *
 * برای شخصی‌سازی، این فایل را در مسیر زیر از پوسته خود کپی کنید:
 * yourtheme/my-gateway/redirect-form.php
 *
 * متغیرهای در دسترس:
 *
 * @var \MyGateway\Operators\Woocommerce\Operator $gateway     نمونه درگاه.
 * @var \WC_Order                                 $order       سفارش جاری.
 * @var string                                    $token       توکن تراکنش بانک.
 * @var string                                    $payment_url آدرس صفحه پرداخت بانک.
 *
 * @package MyGateway
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
?>
<div class="my-gateway-redirect" style="text-align:center;padding:24px 0;">

	<p class="my-gateway-redirect-message">
		<?php esc_html_e( 'در حال انتقال به درگاه امن بانک هستید؛ لطفاً صبر کنید...', 'my-gateway' ); ?>
	</p>

	<form id="my-gateway-redirect-form" method="post" action="<?php echo esc_url( $payment_url ); ?>">
		<input type="hidden" name="token" value="<?php echo esc_attr( $token ); ?>" />

		<button type="submit" class="button alt my-gateway-redirect-button">
			<?php esc_html_e( 'انتقال به صفحه پرداخت بانک', 'my-gateway' ); ?>
		</button>

		<a class="button cancel" href="<?php echo esc_url( $order->get_cancel_order_url() ); ?>">
			<?php esc_html_e( 'انصراف و بازگشت', 'my-gateway' ); ?>
		</a>
	</form>

	<script>
		/* ارسال خودکار فرم پس از بارگذاری صفحه. */
		document.addEventListener( 'DOMContentLoaded', function () {
			var form = document.getElementById( 'my-gateway-redirect-form' );

			if ( form ) {
				setTimeout( function () {
					form.submit();
				}, 1500 );
			}
		} );
	</script>

</div>
