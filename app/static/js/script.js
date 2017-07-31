$(function() {
    $(document).on('change', ':file', function() {
        var input = $(this).parents('.input-group').find(':text'),
            name = $(this).val().split('\\');
        name = name[name.length - 1];
        input.val(name);
    });

    $('.collapse-btn').click(function() {
        $('#'+$(this).data('id')).collapse('toggle');

        if ($(this).html() == 'Show') {
            $(this).html('Hide');
        } else {
            $(this).html('Show');
        }
        $(this).toggleClass('btn-primary').toggleClass('btn-danger');
    });

    $('.clickable-row').click(function() {
        window.location = $(this).data('href');
    });
});
