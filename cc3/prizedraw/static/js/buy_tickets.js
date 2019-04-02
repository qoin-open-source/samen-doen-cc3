$(function() {

    var csrftoken = $.cookie('csrftoken');
    var $pay_highlight = $( "#pay_highlight");
    var $pay_repeat_highlight = $( "#pay_repeat_highlight");
    var initial_ajax_payment_text = $pay_highlight.text();
    var initial_ajax_repeat_payment_text = $pay_repeat_highlight.text();
    var buy_tickets_in_progress = false;
    var $buy_tickets_form = $('#buy_tickets_form');
    var $buy_tickets_form_errors = $( "#buy_tickets_form_errors" );

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

    /*$('#id_repeat_purchase').change(function() {
            alert($(this).checked);
        }
    );*/

    /* attach a submit handler to the payment form */
    $buy_tickets_form.submit(function(event) {
        // if the confirmed input #id_confirmed has been added, submit form normally
        if ($("#id_confirmed").length) {
            return true;
        }

        if (!buy_tickets_in_progress) {
            remove_errors();

            // prevent double clicks / enter buttons
            buy_tickets_in_progress = true;
            $buy_tickets_form_errors.html('');
            $buy_tickets_form_errors.addClass ( 'hide' );
            $('#buy_tickets_form_button').hide();
            $('#buy_tickets_form_spinner').show();

            /* stop form from submitting normally */
            event.preventDefault();

            /* Send the data using post */
            var posting = $.post( buy_tickets_url, $("#buy_tickets_form").serialize() );

            /* Put the results in a div */
            posting.done(function( data ) {
                $buy_tickets_form_errors.html('');
                $buy_tickets_form_errors.addClass ( 'hide' );

                if (data.repeat_purchase) {
                    var template_text = initial_ajax_repeat_payment_text;

                    var num_tickets_start = template_text.indexOf("{{num_tickets}}");
                    template_text = template_text.substring(0, num_tickets_start) + data.num_tickets + template_text.substring(num_tickets_start + 15);

                    var monthly_draws_start = template_text.indexOf("{{monthly_draws}}");
                    if (data.run_indefinitely) {
                        template_text = template_text.substring(0, monthly_draws_start) + 'indefinite' + template_text.substring(monthly_draws_start + 17);
                        var totals_start = template_text.indexOf('This will total');
                        template_text = template_text.substring(0, totals_start) + template_text.substring(totals_start + 70);
                    } else {
                        template_text = template_text.substring(0, monthly_draws_start) + data.num_months + template_text.substring(monthly_draws_start + 17);
                        var amount_start = template_text.indexOf("{{amount}}");
                        template_text = template_text.substring(0, amount_start) + (data.amount * data.num_months) + template_text.substring(amount_start + 10);

                        var total_num_tickets_start = template_text.indexOf("{{total_num_tickets}}");
                        template_text = template_text.substring(0, total_num_tickets_start) + (data.num_tickets * data.num_months) + template_text.substring(total_num_tickets_start + 21);
                    }
                    var add_funds_link_start = template_text.indexOf("{{add_funds_link}}");
                    template_text = template_text.substring(0, add_funds_link_start) +
                        '<a href="' + add_funds_url + '" target="_blank">More info</a>' + template_text.substring(add_funds_link_start + 18);

                    $pay_highlight.hide();
                    $pay_repeat_highlight.html(template_text);
                    $pay_repeat_highlight.show();
                } else {
                    // update the modal warning with current form values
                    var template_text = initial_ajax_payment_text;

                    var num_tickets_start = template_text.indexOf("{{num_tickets}}");
                    template_text = template_text.substring(0, num_tickets_start) + data.num_tickets + template_text.substring(num_tickets_start+15);

                    var amount_start = template_text.indexOf("{{amount}}");
                    //var amount = $('#id_amount').val();
                    template_text = template_text.substring(0, amount_start) + data.amount + template_text.substring(amount_start+10);

                    $pay_highlight.text(template_text);
                    $pay_highlight.show();
                    $pay_repeat_highlight.hide();
                }

                $('#modal_dialog').modal();
                $('#buy_tickets_form_button').show();
                $('#buy_tickets_form_spinner').hide();
                buy_tickets_in_progress = false;
            });
            // deal with form errors
            posting.fail(function( data ) {
                show_errors(data.responseText);
                $('#buy_tickets_form_button').show();
                $('#buy_tickets_form_spinner').hide();

                buy_tickets_in_progress = false;

            });
        }
    });

    // confirm the payment - if modal dialog has been used (ie there is javascript!)
    $("#confirm_payment").click(function(e) {
        if($(this).data('lastClick') + 10000 > new Date().getTime()){

            e.stopPropagation();
            return false;
        }
        $(this).data('lastClick', new Date().getTime());

        var confirmed_input = $("<input>").attr("type", "hidden").attr("id", "id_confirmed").attr("name", "confirmed").val(1);
        $buy_tickets_form.append($(confirmed_input));
        $buy_tickets_form.submit();
    });

    function remove_errors() {

        try {
            $buy_tickets_form_errors.addClass('hide');

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
            $buy_tickets_form_errors.html(gettext('Please check the form for any errors'));
            $buy_tickets_form_errors.addClass ( 'element form-error' );
            $buy_tickets_form_errors.removeClass ( 'hide' );
        } else {
            $buy_tickets_form_errors.html(to_append);
            $buy_tickets_form_errors.addClass ( 'element form-error' );
            $buy_tickets_form_errors.removeClass ( 'hide' );
        }
    }
    location.hash = "#buy_tickets_form_errors";
}
});
