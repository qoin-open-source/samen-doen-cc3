$(function() {
    var csrftoken = $.cookie('csrftoken');
    // this is used to be able to bulk submit all checkboxes if the allonoffswitch is used, 
    // rather than send lots of single submits
    var submit_form = true;
    var all_blocked = true;

    $(".onchange-submit").each( function() {
        if (!this.checked) {
            all_blocked = false;
        }
    });

    if (all_blocked) {
        $('#id_allonoffswitch').prop('checked', true);
        show_blocked();
    } else {
        $('#account_security_form').unblock();        
    }

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

    $('.onchange-submit').on('change', function()    {
        if (submit_form)
            $('#account_security_form').submit();

        if (all_blocked && !this.checked) {
            $('#account_security_form').unblock();  
        }
    });
    $('#id_allonoffswitch').on('change', function() {
        var checkboxes = $('input.onchange-submit');
        // prevent the onchange handler submitting the form
        submit_form = false;
        checkboxes.prop('checked', this.checked);
        // submit the form
        $('#account_security_form').submit();
        // let the onchange handler submit the form
        submit_form = true;
        if (this.checked) {
            show_blocked();
        } else {
            $('#account_security_form').unblock();
        }
    })

    $('#account_security_form').submit(function(event) {
        /* stop form from submitting normally */
        event.preventDefault();

        /* Send the data via ajax */
        $("#account_security_form").ajaxSubmit({
            success: showSuccessMessage,
            error: show_errors,//function(data ) { alert(data); },
        });
    });

    function show_blocked() {
            $('#account_security_form').block({ 
                message: null, 
                overlayCSS:  { 
                    backgroundColor: '#bbb', 
                    opacity:         0.4, 
                    cursor:          null,//'wait' 
                },
            });

    }    

    function showSuccessMessage() {
//        alert ('saved');
    }
    
    function show_errors(the_errors) {
        /*
        var errorObj = $.parseJSON( the_errors.responseText );
        for (var key in errorObj) {
            var item_input, to_append;
            if (key == '__all__'){
                item_input= $('#update_profile_form_errors');
                to_append = errorObj[key];
                item_input.append(to_append);
                item_input.addClass('element').addClass('form-error');
                item_input.removeClass('hide');
            } else {
                item_input= $('#id_' + key);       
                to_append = '<span class="error">' + errorObj[key] + '<br /></span><br />';
                item_input.parent().append(to_append);
                item_input.closest('.element.label').addClass('error'); //parent().parent()
            }
        
        }

        $('#update_profile_form_spinner').hide();
        $('#update_profile_form_button').show();
        update_profile_in_progress = false;*/
        return false;
    }

});


