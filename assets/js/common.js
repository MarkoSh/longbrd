(function ($) {
    var scrollCheck = "start";

    $(window).scroll(function (e) {
        if ($(window).scrollTop() > 100 && scrollCheck == "start") {
            ga('set', 'dimension4', 0);
        }
    });

    (function (i, s, o, g, r, a, m) {
        i['GoogleAnalyticsObject'] = r;
        i[r] = i[r] || function () {
                (i[r].q = i[r].q || []).push(arguments)
            }, i[r].l = 1 * new Date();
        a = s.createElement(o),
            m = s.getElementsByTagName(o)[0];
        a.async = 1;
        a.src = g;
        m.parentNode.insertBefore(a, m)
    })(window, document, 'script', '//www.google-analytics.com/analytics.js', 'ga');
    ga('create', 'UA-62655744-3', 'auto');
    ga('set', 'dimension5', uIP);

    $(".itemFilter a, .load-more").click(function (e) {
        var $this = $(this);
        ga("send", "event", "Клики", "Кнопка " + $this.text(), host, 0);
    });

    $(".navbar-brand").click(function (e) {
        var $this = $(this);
        ga("send", "event", "Клики", "Логотип в шапке", host, 0);
    });

    $("#main-menu a").click(function (e) {
        var $this = $(this);
        ga("send", "event", "Клики", "Пункт меню " + $this.text(), host, 0);
    });

    $(".share-list a").click(function (e) {
        var $this = $(this);
        ga("send", "event", "Клики", "Поделиться " + $this.find('i').attr('class'), host, 0);
    });

    $(".pagination a").click(function (e) {
        var $this = $(this);
        ga("send", "event", "Клики", "Страница " + $this.text(), host, 0);
    });

    var getCookie = function (name) {
        var matches = document.cookie.match(new RegExp(
            "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
        ));
        return matches ? decodeURIComponent(matches[1]) : false;
    };

    $("input[name=phone]").inputmask("+7 (999) 999-99-99");
    $("input[name=email]").inputmask("email");

    setTimeout(function () {
        if (!getCookie('_ga')) {
            ga('set', 'dimension4', 1);
            $.magnificPopup.open({
                showCloseBtn: false,
                items: {
                    src: "#blocker-popup",
                    type: 'inline'
                }
            });
        }
    }, 3000);

    $(".product-btn").magnificPopup({
        callbacks: {
            open: function () {
                var $el = $(this.st.el);
                $(".orderform [name=product]").val($el.data('id'));
                console.warn($el.data('id'));
            }
        },
        showCloseBtn: false
    });
    $(".close-btn").click(function (e) {
        var $this = $(this);
        $.magnificPopup.close();
        return false;
    });

    $("form.orderform")
        .append('<input type="hidden" name="label" value="">')
        .append('<input type="hidden" name="sl" value="">')
        .submit(function (e) {
            var $this = $(this);
            $this.find('[name=sl]').val($(window).scrollTop());
            $this.find('[name=label]').val(getCookie('_ga'));

            if ($this.attr('id') == 'search') {
                return false;
            }

            var phone = $this.find('[name = phone]').val(),
                email = $this.find('[name = email]').val(),
                contact = $this.find('[name = discount]').val();

            ga('set', 'dimension1', phone);
            ga('set', 'dimension2', email);
            ga('set', 'dimension6', contact);

            ga("send", "event", "Отправка форм", "Форма " + $this.attr('id'), host, 10);

            var data = $this.serialize();

            $this.find("[type = submit]").prop('disabled', true);

            $.post('/order', data, function (res) {
                console.warn('success');
                var options = {
                    showCloseBtn: false,
                    items: {
                        src: "#success-popup",
                        type: 'inline'
                    }
                }
                switch (res.status) {
                    case 'nofields':
                        options['items']['src'] = "#nofields-popup";
                        break;
                    case 'no':
                        options['items']['src'] = "#fail-popup";
                        break;
                }
                $.magnificPopup.open(options);
                $this.find("[type = submit]").prop('disabled', false);
                $this.get(0).reset();

                setTimeout(function () {
                    $.magnificPopup.close();
                }, 3000);
            }, 'json').fail(function (res) {
                $this.find("[type = submit]").prop('disabled', false);
                $.magnificPopup.open({
                    showCloseBtn: false,
                    items: {
                        src: "#fail-popup",
                        type: 'inline'
                    }
                });
                setTimeout(function () {
                    $.magnificPopup.close();
                }, 3000);
            });
            return false;
    });

    $(".bxslider").bxSlider({
        auto: !0,
        preloadImages: "all",
        mode: "fade",
        captions: !1,
        controls: !0,
        pause: 4000,
        speed: 1200,
        infiniteLoop: false,
        onSliderLoad: function () {
            $(".bxslider>li .slide-inner").eq(1).addClass("active-slide"), $(".slide-inner.active-slide .slider-title").addClass("wow animated bounceInDown"), $(".slide-inner.active-slide .slide-description").addClass("wow animated bounceInRight"), $(".slide-inner.active-slide .btn").addClass("wow animated zoomInUp")
        },
        onSlideAfter: function (e, i, n) {
            console.log(n), $(".active-slide").removeClass("active-slide"), $(".bxslider>li .slide-inner").eq(n + 1).addClass("active-slide"), $(".slide-inner.active-slide").addClass("wow animated bounceInRight")
        },
        onSlideBefore: function () {
            $(".slide-inner.active-slide").removeClass("wow animated bounceInRight"), $(".one.slide-inner.active-slide").removeAttr("style")
        }
    }), $(document).ready(function () {
        function e() {
            return "ontouchstart" in document.documentElement
        }

        function i() {
            var center = function () {
                var defLatLng = [59.936285, 30.415153];
                if ($(window).width() < 900) {
                    defLatLng = [59.929076, 30.357339];
                }
                $(window).resize(function () {
                    if ($(window).width() < 900) {
                        defLatLng = [59.929076, 30.357339];
                    }
                });
                return defLatLng;
            };
            if ("undefined" != typeof google) {
                var i = {
                    center: center(),
                    zoom: 11,
                    mapTypeControl: !0,
                    mapTypeControlOptions: {style: google.maps.MapTypeControlStyle.DROPDOWN_MENU},
                    navigationControl: !0,
                    scrollwheel: 0,
                    streetViewControl: !0
                };
                e() && (i.draggable = !0), $("#googleMaps").gmap3({
                    map: {options: i},
                    marker: {
                        values: [
                            {
                                address: "ул. Восстания, 24, Санкт-Петербург, 191014",
                                data: {
                                    title: "Justx3m Boardshop",
                                    site: "https://justx3m.ru/",
                                    phone: "8 812 958-78-93",
                                    logo: "/images/sponsors/justx3m.png"
                                }
                            },
                            {
                                address: "Транспортный пер., 2А, Санкт-Петербург, Ленинградская область, 191119",
                                data: {
                                    title: "NevskySurf",
                                    site: "http://nevskysurf.ru/",
                                    phone: "8 952 363-23-14",
                                    logo: "/images/sponsors/nevskysurf.png"
                                }
                            },
                            {
                                address: "Московский пр., 206к1, Санкт-Петербург, 196135",
                                data: {
                                    title: "MentalShop",
                                    site: "http://mentalshop.ru/",
                                    phone: "8 812 243-90-38",
                                    logo: "/images/sponsors/mentalshop.png"
                                }
                            },
                            {
                                address: "Пушкинская ул., 12, Санкт-Петербург, Ленинградская область, 191040",
                                data: {
                                    title: "Balance Skate & Snow",
                                    site: "http://www.balanceshop.ru/",
                                    phone: "8 812 764-48-05",
                                    logo: "/images/sponsors/balanceshop.png"
                                }
                            },
                            {
                                address: "Приморский просп., 13, Санкт-Петербург, 197183",
                                data: {
                                    title: "Велострайк",
                                    site: "http://velostrike.ru/",
                                    phone: "8 800 555-39-19",
                                    logo: "/images/sponsors/velostrike.png"
                                }
                            },
                            {
                                address: "Садовая ул., 28/30, Санкт-Петербург, 191023",
                                data: {
                                    title: "Сквот",
                                    site: "http://www.skvot.com/",
                                    phone: "8 800 100-41-69",
                                    logo: "/images/sponsors/skvot.png"
                                }
                            },
                            {
                                address: "ТРК \"Сити Молл\", 2 этаж, Коломяжский пр-кт 17к1литА, Санкт-Петербург, 197341",
                                data: {
                                    title: "Сквот",
                                    site: "http://www.skvot.com/",
                                    phone: "8 981 751-37-84",
                                    logo: "/images/sponsors/skvot.png"
                                }
                            }
                        ],
                        events: {
                            mouseover: function (marker, event, context) {
                                $("#balloon .shoplogo").attr('src', context.data.logo);
                                $("#balloon .shopname").text(context.data.title);
                                var html = $("#balloon").clone().get(0);
                                var map = $(this).gmap3("get"),
                                    infowindow = $(this).gmap3({get: {name: "infowindow"}});
                                if (infowindow) {
                                    infowindow.open(map, marker);
                                    infowindow.setContent(html);
                                } else {
                                    $(this).gmap3({
                                        infowindow: {
                                            anchor: marker,
                                            options: {content: html}
                                        }
                                    });
                                }
                            },
                            mouseout: function () {
                                var infowindow = $(this).gmap3({get: {name: "infowindow"}});
                                if (infowindow) {
//                                    infowindow.close();
                                }
                            }
                        }
                    }
                });
            }
        }

        $("#masthead #main-menu").onePageNav(), i()
    });

    // $('#waypoint').waypoint({
    //     handler: function (direction) {
    //         if (direction == 'down') {
    //             var active = $('.pagination li.active');
    //             var next = active.next();
    //             if (next.length) {
    //                 active.removeClass('active');
    //                 next.addClass('active');
    //                 var href = next.find('a').attr('href');
    //                 $.get(href, function (res) {
    //                     $('.posts-wrapper').append($('.posts-wrapper', res).html());
    //                     history.pushState(null, null, href);
    //                     Waypoint.refreshAll();
    //                     $("body").trigger('scrolled');
    //                 });
    //             }
    //         }
    //
    //     },
    //     offset: "100%"
    // });
})(jQuery);

var Share = {
    vkontakte: function(purl, ptitle, pimg, text) {
        url  = 'http://vkontakte.ru/share.php?';
        url += 'url='          + encodeURIComponent(purl);
        url += '&title='       + encodeURIComponent(ptitle);
        url += '&description=' + encodeURIComponent(text);
        url += '&image='       + encodeURIComponent(pimg);
        url += '&noparse=true';
        Share.popup(url);
    },
    odnoklassniki: function(purl, text) {
        url  = 'http://www.odnoklassniki.ru/dk?st.cmd=addShare&st.s=1';
        url += '&st.comments=' + encodeURIComponent(text);
        url += '&st._surl='    + encodeURIComponent(purl);
        Share.popup(url);
    },
    facebook: function(purl, ptitle, pimg, text) {
        url  = 'http://www.facebook.com/sharer.php?s=100';
        url += '&p[title]='     + encodeURIComponent(ptitle);
        url += '&p[summary]='   + encodeURIComponent(text);
        url += '&p[url]='       + encodeURIComponent(purl);
        url += '&p[images][0]=' + encodeURIComponent(pimg);
        Share.popup(url);
    },
    twitter: function(purl, ptitle) {
        url  = 'http://twitter.com/share?';
        url += 'text='      + encodeURIComponent(ptitle);
        url += '&url='      + encodeURIComponent(purl);
        url += '&counturl=' + encodeURIComponent(purl);
        Share.popup(url);
    },
    mailru: function(purl, ptitle, pimg, text) {
        url  = 'http://connect.mail.ru/share?';
        url += 'url='          + encodeURIComponent(purl);
        url += '&title='       + encodeURIComponent(ptitle);
        url += '&description=' + encodeURIComponent(text);
        url += '&imageurl='    + encodeURIComponent(pimg);
        Share.popup(url);
    },

    popup: function(url) {
        window.open(url,'','toolbar=0,status=0,width=626,height=436');
    }
};