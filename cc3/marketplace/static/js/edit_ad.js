$(function() {
    var csrftoken = $.cookie('csrftoken');

    $('.form-row.inline.adimage_set').formset({
        prefix: 'adimage_set',
        addText: gettext("+ Add Image"),                   // Text for the add link
        deleteText: gettext("+ Remove Image"),              // Text for the delete link
        addCssClass: 'add-row element add-button pull-right',   // CSS class applied to the add link
        deleteCssClass: 'delete-row element add-button reverse',
        deleteCssClassSelector: 'delete-row.element.add-button.reverse'
    });

    var place_ad_in_progress = false;
    
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    /* attach a submit handler to the advert update form */
    $("#place_ad_form").submit(function(event) {
        if (typeof(dropzone_ref) != "undefined"){

            var fs = dropzone_ref.files;
            var fs_length = fs.length;
            var any_uploading = false;
            for (var i = 0; i < fs_length; i++) {
                var f_status = fs[i].status;
                // catch any uploading, about to upload or only just added.
                // ignore errors and successes
                if(f_status == "uploading" || f_status == "added" || f_status == "queued") {
                    any_uploading = true;
                }
            }
            if (any_uploading == true) {
                $('#modal_dialog').modal();
                return false;
            }
        }

        if (!place_ad_in_progress) {
            remove_errors();
            var $place_ad_form_errors = $( "#place_ad_form_errors" );
            
            // prevent double clicks / enter buttons
            place_ad_in_progress = true;
            $place_ad_form_errors.html('');
            $place_ad_form_errors.addClass ( 'hide' );
            $('#place_ad_form_button').hide();
            $('#place_ad_form_spinner').show();
            
            // stop form from submitting normally
            event.preventDefault();

            // make sure tinyMCE delivers to the textarea for POSTing
            tinyMCE.triggerSave();

            // Send the data via ajax - to avoid loosing file info if invalid
            $("#place_ad_form").ajaxSubmit(
                {
                    success:showSuccessPage,
                    error: function(data ) { 
                        remove_errors();
                        show_errors(data.responseText); 
                        $('#place_ad_form_spinner').hide();
                        $('#place_ad_form_button').show();
                        place_ad_in_progress = false;
                    }
                }
            );
        }
    });
});

function remove_errors() {

    try {
        item_input= $('#place_ad_form_errors');
        item_input.addClass('hide');

        var span_error_classes = $('span.error');
        span_error_classes.each(function(){
            this.remove();
        });

        var div_error_classes = $('div.error');
        div_error_classes.each(function(){
            this.removeClass('error');
        });
    }
    catch (e) {
        // not too worried with exceptions removing error spans/divs
    }

    $('.error').removeClass('error');
}

function show_errors(the_errors) {
    var errorObj = $.parseJSON( the_errors );
    for (var key in errorObj) {
        var item_input = $('#id_' + key);
        var to_append = '<span class="error">' + errorObj[key] + '<br /></span>';
        var $place_ad_form_errors = $( "#place_ad_form_errors" );

        // hack to get category checkboxes to show error
        if ('#id_' + key == '#id_category'){
            item_input = $('#id_category_0').parent().parent().parent().parent();
            to_append = '<span class="error" style="clear:both;">' + errorObj[key] + '<br /></span>';
        }

        // hack to get community created by to show error correctly
        if ('#id_' + key == '#id_created_by') {
            item_input.parent().parent().addClass('error');
        }

        if (item_input.length) {
            item_input.parent().append(to_append);
            item_input.parent().parent().parent().addClass('error');
            $place_ad_form_errors.html(gettext('Please check the form for any errors'));
            $place_ad_form_errors.addClass ( 'element form-error' );
            $place_ad_form_errors.removeClass ( 'hide' );
        } else {
            $place_ad_form_errors.html(to_append);
            $place_ad_form_errors.addClass ( 'element form-error' );
            $place_ad_form_errors.removeClass ( 'hide' );
        }
    }
    location.hash = "#place_ad_form_errors";
}

function showSuccessPage() {
     window.location.replace(return_url);
}
