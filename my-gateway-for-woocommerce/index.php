<?php
/**
 * Plugin Name:       My Gateway for WooCommerce
 * Plugin URI:        https://example.com/my-gateway
 * Description:       درگاه پرداخت حرفه‌ای، امن و ماژولار برای ووکامرس — معماری شیءگرا (OOP)، استاندارد PSR-4، لاگ پیشرفته Monolog با تاریخ شمسی، مکانیزم Webhook و لایه‌های امنیتی ضدجعل.
 * Version:           1.0.0
 * Requires at least: 5.8
 * Requires PHP:      7.4
 * Author:            MyGateway Team
 * Author URI:        https://example.com
 * License:           GPL v2 or later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       my-gateway
 * Domain Path:       /languages
 * WC requires at least: 5.0
 * WC tested up to:   9.5
 *
 * @package MyGateway
 */

// جلوگیری از دسترسی مستقیم به فایل.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/*
|--------------------------------------------------------------------------
| ثابت‌های سراسری افزونه
|--------------------------------------------------------------------------
*/
define( 'MY_GATEWAY_VERSION', '1.0.0' );
define( 'MY_GATEWAY_PLUGIN_FILE', __FILE__ );
define( 'MY_GATEWAY_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );
define( 'MY_GATEWAY_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'MY_GATEWAY_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'MY_GATEWAY_MIN_PHP', '7.4' );
define( 'MY_GATEWAY_MIN_WC', '5.0' );

/*
|--------------------------------------------------------------------------
| بارگذاری Autoloader کامپوزر (PSR-4)
|--------------------------------------------------------------------------
| اگر vendor نصب نشده باشد، به‌جای Fatal Error یک اعلان مدیریتی نمایش
| داده می‌شود تا سایت از دسترس خارج نشود.
*/
$my_gateway_autoloader = MY_GATEWAY_PLUGIN_DIR . 'vendor/autoload.php';

if ( ! file_exists( $my_gateway_autoloader ) ) {
	add_action(
		'admin_notices',
		static function () {
			printf(
				'<div class="notice notice-error"><p><strong>%s</strong> %s <code>composer install</code> %s</p></div>',
				esc_html__( 'My Gateway:', 'my-gateway' ),
				esc_html__( 'وابستگی‌های کامپوزر نصب نشده‌اند. لطفاً در پوشه افزونه دستور', 'my-gateway' ),
				esc_html__( 'را اجرا کنید.', 'my-gateway' )
			);
		}
	);

	return;
}

require_once $my_gateway_autoloader;

/*
|--------------------------------------------------------------------------
| راه‌اندازی هسته افزونه
|--------------------------------------------------------------------------
| تمام هوک‌ها و منطق بوت‌استرپ در فایل src/init.php مدیریت می‌شود.
*/
require_once MY_GATEWAY_PLUGIN_DIR . 'src/init.php';

my_gateway_bootstrap();
