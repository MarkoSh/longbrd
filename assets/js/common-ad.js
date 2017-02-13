(function ($) {
    tinymce.init({
        selector: "textarea.editor",
        theme: "modern",
        forced_root_block : false,
        force_p_newlines: true,
        force_br_newlines: true,
        menubar: false
    });
    $('form[id*=editor-]').submit(function (e) {
        tinymce.triggerSave();
        var $this = $(this);
        $this.addClass('process');
        var data = $this.serialize();
        $.post('/savepost', data, function (res) {
            $this.removeClass('process');
        }).fail(function (res) {

        });
        return false;
    });
    $('[type=button]').click(function (e) {
        var $this = $(this);
        var btnTxt = $this.val();
        var postid = $this.data('postid');
        if ($this.hasClass('remove')) {
            var result = confirm('Удалить пост?');
            if (result) {
                $.get('/removepost', {
                    postid: postid
                }, function (res) {
                    $('#editor-' + postid).remove();
                }).fail(function (res) {

                });
            }
        }
        if ($this.hasClass('publish')) {
            var sts = $this.parents('form').find('.stsicon');
            sts.removeClass('fa-check-circle').addClass('fa-cog fa-spin');
            $.get('/publishpost', {
                postid: postid
            }, function (res) {
                sts.removeClass('fa-cog fa-spin');
                if (res == 1) {
                    sts.addClass('fa-check-circle');
                } else {
                    sts.removeClass('fa-check-circle');
                }
            }).fail(function (res) {

            });
        }
    });

})(jQuery);