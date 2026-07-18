<?php
/**
 * قالب نمایش درگاه در صفحه تسویه‌حساب کلاسیک.
 *
 * برای شخصی‌سازی، این فایل را در مسیر زیر از پوسته خود کپی کنید:
 * yourtheme/my-gateway/payment-form.php
 *
 * متغیرهای در دسترس:
 *
 * @var \MyGateway\Operators\Woocommerce\Operator $gateway     نمونه درگاه.
 * @var string                                    $description توضیحات درگاه.
 * @var bool                                      $is_sandbox  فعال بودن حالت آزمایشی.
 *
 * @package MyGateway
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}
?>
<div class="my-gateway-payment-form">

	<?php if ( ! empty( $description ) ) : ?>
		<p class="my-gateway-description">
			<?php echo wp_kses_post( wptexturize( $description ) ); ?>
		</p>
	<?php endif; ?>

	<?php if ( $is_sandbox ) : ?>
		<p class="my-gateway-sandbox-notice" style="color:#996b00;background:#fff8e5;border:1px solid #f0c33c;border-radius:4px;padding:8px 12px;">
			<?php esc_html_e( 'درگاه در حالت آزمایشی است؛ هیچ تراکنش واقعی انجام نمی‌شود.', 'my-gateway' ); ?>
		</p>
	<?php endif; ?>

	<p class="my-gateway-redirect-notice" style="font-size:0.9em;opacity:0.8;">
		<?php esc_html_e( 'پس از ثبت سفارش، به صفحه امن بانک منتقل می‌شوید.', 'my-gateway' ); ?>
	</p>

</div>
