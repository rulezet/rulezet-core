
// Toggle API key visibility. Exposed as window.bindApiKeyToggle so callers
// that re-render the API key card in place (e.g. after regenerating it) can
// re-bind the toggle without a page reload.
(function() {
    function bindApiKeyToggle() {
        var $btn = $('#toggle-api-key');
        var $key = $('#api-key');
        if (!$btn.length || !$key.length) return;

        $btn.off('click').on('click', function() {
            var visible = $btn.attr('data-visible') === 'true';
            if (visible) {
                // hide
                $key.addClass('blurred');
                $btn.attr('data-visible', 'false');
                $btn.attr('aria-pressed', 'false');
                $btn.attr('aria-label', 'Show API key');
                $btn.attr('title', 'Show API key');
                $btn.find('i').removeClass('fa-eye-slash').addClass('fa-eye');
            } else {
                // show
                $key.removeClass('blurred');
                $btn.attr('data-visible', 'true');
                $btn.attr('aria-pressed', 'true');
                $btn.attr('aria-label', 'Hide API key');
                $btn.attr('title', 'Hide API key');
                $btn.find('i').removeClass('fa-eye').addClass('fa-eye-slash');
            }
        });
    }

    window.bindApiKeyToggle = bindApiKeyToggle;
    $(bindApiKeyToggle);
})();
