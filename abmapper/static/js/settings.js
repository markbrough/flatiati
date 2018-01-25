function resetFormGroup(input) {
  $(input).parent().parent().removeClass("has-success has-error has-feedback");
  $(input).parent().find(".form-control-feedback").remove();
  $(input).parent().find(".form-control-status").remove();
  $(input).parent().parent().find(".help-block").remove();
}
function successFormGroup(input) {
  $(input).parent().parent().addClass("has-success has-feedback");
  $(input).after('<span class="glyphicon glyphicon-floppy-saved form-control-feedback" aria-hidden="true"></span> \
  <span class="sr-only form-control-status">(success)</span>');
}
function errorFormGroup(input, optional_text) {
  $(input).parent().parent().addClass("has-error has-feedback");
  if (optional_text) {
    $(input).parent().after('<span class="help-block">' + optional_text + '</span>');
  }
  $(input).after('<span class="glyphicon glyphicon-floppy-remove form-control-feedback" aria-hidden="true"></span> \
  <span class="sr-only form-control-status">(error)</span>');
}
$("#confirm-delete").on('show.bs.modal', function(e) {
  $(this).find(".btn-ok").on("click", function(f) {
    deleteReportingOrg(e.relatedTarget);
    $("#confirm-delete").modal("hide");
  });
});

function deleteReportingOrg(target) {
  var data = {
    "reporting_org_id": $(target).closest("tr").attr("data-reporting-org-id"),
    "action": "delete"
  }
  $.post(api_reporting_orgs_url, data, 
    function(returndata){
      if (returndata == 'False'){
          alert("There was an error deleting that reporting org.");
      } else {
        $("tr#reporting-org-" + data["reporting_org_id"]).fadeOut();
      }
    }
  );
}

$(document).on("click", ".addReportingOrg", function(e) {
  e.preventDefault();
  var data = {
    "action": "add"
  }
  $.post(api_reporting_orgs_url, data, 
    function(returndata){
      if (returndata == 'False'){
          alert("There was an error adding that reporting org.");
      } else {
        var row_reporting_org_template = $('#row-reporting-org-template').html();
        var data = {
          "id": returndata
        }
      	var rendered_row = Mustache.render(row_reporting_org_template, data);
      	$('#reporting-orgs-rows').append(rendered_row);
      }
    }
  );
});

// REPORTING ORGS
var updateReportingOrgs = function(reporting_orgs) {
  // Render reporting-orgs template
	var reporting_org_template = $('#reporting-orgs-template').html();
	Mustache.parse(reporting_org_template);   // optional, speeds up future uses
  
	partials = {"row-reporting-org-template": $('#row-reporting-org-template').html()};
  
	var rendered = Mustache.render(reporting_org_template, reporting_orgs, partials);
	$('#reporting-orgs').html(rendered);
}

var setupReportingOrgsForm = function(reporting_orgs) {
  updateReportingOrgs(reporting_orgs);
};
var reporting_org_template;
var reporting_org_data;
var setupReportingOrgs = function() {
	$.getJSON(api_reporting_orgs_url, function(data) {
      reporting_org_data = data;
      setupReportingOrgsForm(data);
	});
};
setupReportingOrgs()

$(document).on("change", "#reporting-orgs input[type=text], input[type=checkbox]", function(e) {
  var data = {
    'reporting_org_id': $(this).closest("tr").attr("data-reporting-org-id"),
    'attr': this.name,
    'value': this.value,
  }
  if (data["attr"] == "active") {
    if (this.checked) {
      data["value"] = true;
    } else {
      data["value"] = false;
    }
  }
  var input = this;
  resetFormGroup(input);
  $.post(api_update_reporting_orgs_url, data, function(resultdata) {
    successFormGroup(input);
  }).fail(function(){
    errorFormGroup(input);
  });
});