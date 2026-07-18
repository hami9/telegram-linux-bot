/**
 * ثبت متد پرداخت My Gateway در صفحه تسویه‌حساب بلوکی ووکامرس.
 *
 * این فایل بدون نیاز به Build (وانیلا) نوشته شده و از پکیج‌های سراسری
 * wc و wp استفاده می‌کند.
 *
 * @package MyGateway
 */
( function () {
	'use strict';

	if ( ! window.wc || ! window.wc.wcBlocksRegistry || ! window.wc.wcSettings ) {
		return;
	}

	var registerPaymentMethod = window.wc.wcBlocksRegistry.registerPaymentMethod;
	var getSetting = window.wc.wcSettings.getSetting;
	var createElement = window.wp.element.createElement;
	var decodeEntities = window.wp.htmlEntities.decodeEntities;
	var __ = window.wp.i18n.__;

	// داده‌های تزریق‌شده از PaymentMethodBlock::get_payment_method_data.
	var settings = getSetting( 'my_gateway_data', {} );

	var defaultTitle = __( 'پرداخت امن آنلاین', 'my-gateway' );
	var title = decodeEntities( settings.title || '' ) || defaultTitle;
	var description = decodeEntities( settings.description || '' );

	/**
	 * برچسب متد پرداخت (عنوان + آیکون درگاه).
	 *
	 * @param {Object} props پراپ‌های کامپوننت.
	 * @return {Object} المنت React.
	 */
	var Label = function ( props ) {
		var label = createElement(
			'span',
			{ style: { width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between' } },
			createElement( 'span', null, title ),
			settings.icon
				? createElement( 'img', {
						src: settings.icon,
						alt: title,
						style: { maxHeight: '24px' },
				  } )
				: null
		);

		return props && props.components && props.components.PaymentMethodLabel
			? createElement( props.components.PaymentMethodLabel, { text: title } )
			: label;
	};

	/**
	 * محتوای متد پرداخت (توضیحات + هشدار حالت آزمایشی).
	 *
	 * @return {Object} المنت React.
	 */
	var Content = function () {
		var children = [];

		if ( description ) {
			children.push( createElement( 'p', { key: 'desc' }, description ) );
		}

		if ( settings.sandbox ) {
			children.push(
				createElement(
					'p',
					{
						key: 'sandbox',
						style: {
							color: '#996b00',
							background: '#fff8e5',
							border: '1px solid #f0c33c',
							borderRadius: '4px',
							padding: '8px 12px',
						},
					},
					__( 'درگاه در حالت آزمایشی است؛ هیچ تراکنش واقعی انجام نمی‌شود.', 'my-gateway' )
				)
			);
		}

		return createElement( 'div', { className: 'my-gateway-block-content' }, children );
	};

	registerPaymentMethod( {
		name: 'my_gateway',
		label: createElement( Label ),
		content: createElement( Content ),
		edit: createElement( Content ),
		canMakePayment: function () {
			return true;
		},
		ariaLabel: title,
		supports: {
			features: settings.supports || [ 'products' ],
		},
	} );
} )();
