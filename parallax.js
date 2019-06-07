$(document).ready(function () {
    function filterPath(string) { return string.replace(/^\//, '').replace(/(index|default).[a-zA-Z]{3,4}$/, '').replace(/\/$/, ''); }
    $('a[href*=#]').each(function () {
        if (filterPath(location.pathname) == filterPath(this.pathname) && location.hostname == this.hostname && this.hash.replace(/#/, '')) {
            var $targetId = $(this.hash)
            $targetAnchor = $('[name=' + this.hash.slice(1) + ']');
            var $target = $targetId.length ? $targetId : $targetAnchor.length ? $targetAnchor : false;
            if ($target) {
                var targetOffset = $target.offset().top; $(this).click(function () {
                    $('html, body').animate({ scrollTop: targetOffset }, 400); return false;
                });
            }
        }
    });
});

$(document).ready(function () {
    $('a[href*=#]').each(function () {
        if (location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '')
            && location.hostname == this.hostname
            && this.hash.replace(/#/, '')) {
            var $targetId = $(this.hash), $targetAnchor = $('[name=' + this.hash.slice(1) + ']');
            var $target = $targetId.length ? $targetId : $targetAnchor.length ? $targetAnchor : false;
            if ($target) {
                var targetOffset = $target.offset().top;
                $(this).click(function () {
                    $("#nav li a").removeClass("active");
                    $(this).addClass('active');
                    $('html, body').animate({ scrollTop: targetOffset }, 1000);
                    return false;
                });
            }
        }
    });

});

$('html, body').animate({ scrollTop: targetOffset }, 10000);