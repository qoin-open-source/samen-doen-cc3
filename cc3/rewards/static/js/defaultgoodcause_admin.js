// no conflict likely here - so use standard $ for jquery
    var $ = django.jQuery;

    $(function($){
      var causes_by_community = [];
      // Load causes info.
      $.ajax({
        url: admin_causes_list_url,
        success: function(text) {
          var lines = text.split('\n');
          for (var n=0, len=lines.length, line; n<len; n++) {
            line = lines[n].split('\t');

            if (typeof(causes_by_community[line[0]]) == 'undefined')
                causes_by_community[line[0]] = [];

            causes_by_community[line[0]].push([line[1], line[2]]);
          }
          var community_id_selected_onload = $('#id_community').val();
          if (community_id_selected_onload != "") {
            var current_cause_selected_index = parseInt($("#id_cause").val());
            var options = '';
            var cause_options = causes_by_community[community_id_selected_onload];
            for (var cause_index in cause_options) {
              options += '<option value="' + cause_options[cause_index][0] + '"';
              if (parseInt(cause_options[cause_index][0]) == current_cause_selected_index)
                options += ' selected';
              options += '>' + cause_options[cause_index][1] + '</option>';
            }
            $("#id_cause").html(options);
          }
        }
      });

      $('#id_community').change(function() {
        var community_id_selected = $(this).val();
        var current_cause_selected_index = parseInt($("#id_cause").val());
        var options = '';
        var cause_options = causes_by_community[community_id_selected];
        for (var cause_index in cause_options) {
          options += '<option value="' + cause_options[cause_index][0] + '"';
          if (parseInt(cause_options[cause_index][0]) == current_cause_selected_index)
            options += ' selected';
          options += '>' + cause_options[cause_index][1] + '</option>';
        }
        $("#id_cause").html(options);
      });
    });
