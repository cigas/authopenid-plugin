/*
	Simple OpenID Plugin
	http://code.google.com/p/openid-selector/
	
	This code is licensed under the New BSD License.
*/

var providers;
var openid;
(function ($) {
openid = {
	version : '1.3', // version constant
	demo : false,
	demo_text : null,
	cookie_expires : 6 * 30, // 6 months.
	cookie_name : 'openid_provider',
	cookie_path : '/',

	img_path : 'images/',
	locale : null, // is set in openid-<locale>.js
	sprite : null, // usually equals to locale, is set in
	// openid-<locale>.js
	signin_text : null, // text on submit button on the form
	all_small : false, // output large providers w/ small icons
	no_sprite : false, // don't use sprite image
	image_title : '{provider}', // for image title

	input_id : null,
	provider_url : null,
	provider_id : null,

	/**
	 * Class constructor
	 * 
	 * @return {Void}
	 */
	init : function(input_id) {
		providers = $.extend({}, providers_large, providers_small);
		var openid_btns = $('#openid_btns');
		this.input_id = input_id;
		$('#openid_choice').show();
		$('#openid_input_area').empty();
		var i = 0;
		// add box for each provider
		var id, box;
		for (id in providers_large) {
                    var provider = providers_large[id];
                    if (this.want_provider(id)) {
			openid_btns.append(this.getBoxHTML(
                            id, provider,
                            (this.all_small ? 'small' : 'large'), i));
                    }
                    if (provider.image === undefined)
                        i++;    // built-in provider
		}
		if (providers_small) {
		    openid_btns.append('<br/>');
		    for (id in providers_small) {
                        var provider = providers_small[id];
                        if (this.want_provider(id)) {
			    openid_btns.append(this.getBoxHTML(
                                id, provider, 'small', i));
                        }
                        if (provider.image === undefined)
                            i++;    // built-in provider
                    }
		}
		$('#openid_form').submit(this.submit);
		var box_id = this.readCookie();
		if (box_id) {
			this.signin(box_id, true);
		}
	},

    want_provider : function(box_id) {
        var providers = this.show_providers;
        if (!providers || providers.length == 0)
            return true;
        return $.inArray(box_id, providers) >= 0;
    },
	/**
	 * @return {String}
	 */
	getBoxHTML : function(box_id, provider, box_size, index) {
            var title = this.image_title.replace('{provider}', provider.name);
            var href = "javascript:openid.signin('" + box_id +"');"
            var css_class = box_id + " openid_" + box_size + "_btn";
            var img_url = provider.image;
            if (! img_url) {
                if (this.no_sprite) {
		    var image_ext = box_size == 'small' ? '.ico.gif' : '.gif';
                    img_url = this.img_path + '../images.' + box_size
                        + '/' + box_id + image_ext;
                }
                else {
                    var sprite_url = this.img_path + 'openid-providers-'
                        + this.sprite + '.png';
                }
            }
            if (sprite_url) {
	        var x = box_size == 'small' ? -index * 24 : -index * 100;
	        var y = box_size == 'small' ? -60 : 0;
                var style = "background: #FFF url(" + sprite_url + ");"
                    + "background-position: " + x + "px " + y + "px";
            } else {
                style = "background: #fff url(" + img_url + ")"
                    + " no-repeat center center;"
            }
            return '<a title="' + title + '" href="' + href
                + '" style="' + style + '" class="' + css_class + '"></a>';
	},

	/**
	 * Provider image click
	 * 
	 * @return {Void}
	 */
	signin : function(box_id, onload) {
		var provider = providers[box_id];
		if (!provider) {
			return;
		}
		this.highlight(box_id);
		this.setCookie(box_id);
		this.provider_id = box_id;
		this.provider_url = provider.url;
		// prompt user for input?
		if (provider.label) {
			this.useInputBox(provider);
		} else {
			$('#openid_input_area').empty();
			if (!onload) {
				$('#openid_form').submit();
			}
		}
	},

	/**
	 * Sign-in button click
	 * 
	 * @return {Boolean}
	 */
	submit : function() {
		var url = openid.provider_url;
		if (url) {
			url = url.replace('{username}', $('#openid_username').val());
			openid.setOpenIdUrl(url);
		}
		if (openid.demo) {
			alert(openid.demo_text + "\r\n" + document.getElementById(openid.input_id).value);
			return false;
		}
		if (url && url.indexOf("javascript:") == 0) {
			url = url.substr("javascript:".length);
			eval(url);
			return false;
		}
		return true;
	},

	/**
	 * @return {Void}
	 */
	setOpenIdUrl : function(url) {
		var hidden = document.getElementById(this.input_id);
		if (hidden != null) {
			hidden.value = url;
		} else {
			$('#openid_form').append('<input type="hidden" id="' + this.input_id + '" name="' + this.input_id + '" value="' + url + '"/>');
		}
	},

	/**
	 * @return {Void}
	 */
	highlight : function(box_id) {
		// remove previous highlight.
		var highlight = $('#openid_highlight');
		if (highlight) {
			highlight.replaceWith($('#openid_highlight a')[0]);
		}
		// add new highlight.
		$('.' + box_id).wrap('<div id="openid_highlight"></div>');
	},

	setCookie : function(value) {
		var date = new Date();
		date.setTime(date.getTime() + (this.cookie_expires * 24 * 60 * 60 * 1000));
		var expires = "; expires=" + date.toGMTString();
		document.cookie = this.cookie_name + "=" + value + expires + "; path=" + this.cookie_path;
	},

	readCookie : function() {
		var nameEQ = this.cookie_name + "=";
		var ca = document.cookie.split(';');
		for ( var i = 0; i < ca.length; i++) {
			var c = ca[i];
			while (c.charAt(0) == ' ')
				c = c.substring(1, c.length);
			if (c.indexOf(nameEQ) == 0)
				return c.substring(nameEQ.length, c.length);
		}
		return null;
	},

	/**
	 * @return {Void}
	 */
	useInputBox : function(provider) {
		var input_area = $('#openid_input_area');
		var html = '';
		var id = 'openid_username';
		var value = '';
		var label = provider.label;
		var style = '';
		if (label) {
			html = '<p>' + label + '</p>';
		}
		if (provider.name == 'OpenID') {
			id = this.input_id;
			value = 'http://';
			style = 'background: #FFF url(' + this.img_path + 'openid-inputicon.gif) no-repeat scroll 0 50%; padding-left:18px;';
		}
		html += '<input id="' + id + '" type="text" style="' + style + '" name="' + id + '" value="' + value + '" />'
				+ '<input id="openid_submit" type="submit" value="' + this.signin_text + '"/>';
		input_area.empty();
		input_area.append(html);
		$('#' + id).focus();
	},

	setDemoMode : function(demoMode) {
		this.demo = demoMode;
	}
};
})(jQuery);