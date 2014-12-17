var width = 600,
    height = 500,
    radius = Math.min(width, height) / 2;

var color = d3.scale.category20c();

var svg = d3.select(".budget-chart").append("svg").append("g")

svg.append("g")
	.attr("class", "slices");
svg.append("g")
	.attr("class", "labels");
svg.append("g")
	.attr("class", "lines");

var pie = d3.layout.pie()
    .value(function(d) { return d.before_value; })
    .sort(null);

var arc = d3.svg.arc()
	.outerRadius(radius * 0.8)
	.innerRadius(radius * 0.4);

var outerArc = d3.svg.arc()
	.innerRadius(radius * 0.9)
	.outerRadius(radius * 0.9);

svg.attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

function formatAsMillions(value){
    return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

d3.csv("budgetstats.csv", type, function(error, data) {
  var path = svg.datum(data).selectAll("path")
      .data(pie)
      .enter().append("path")
      .attr("fill", function(d, i) { return color(i); })
      .attr("title", function(d) { return d['data']['budget_name']; })
      .attr("before", function(d) { return d['data']['before_value']; })
      .attr("after", function(d) { return d['data']['after_value']; })
      .attr("d", arc)
      .each(function(d) { this._current = d; })
	  .on("mouseover", function(){
                d3.select("#budgetselected").text(d3.select(this).attr("title"));
                d3.select("#budgetbefore").text(formatAsMillions(d3.select(this).attr("before")));
                d3.select("#budgetafter").text(formatAsMillions(d3.select(this).attr("after")));
                d3.select(".budgetafter-dt").style("visibility", "visible");
                d3.select(".budgetbefore-dt").style("visibility", "visible");
        })
	  .on("mouseout", function(){
                d3.select("#budgetselected").text("Hover over a sector for details.");
                d3.select("#budgetbefore").text("");
                d3.select("#budgetafter").text("");
                d3.select(".budgetafter-dt").style("visibility", "hidden");
                d3.select(".budgetbefore-dt").style("visibility", "hidden");
        });

  d3.selectAll("input")
      .on("change", change);

  var timeout = setTimeout(function() {
    d3.select("input[value=\"after_value\"]").property("checked", true).each(change);
  }, 2000);

  function change() {
    var value = this.value;
    clearTimeout(timeout);
    pie.value(function(d) { return d[value]; }); // change the value function
    path = path.data(pie); // compute the new angles
    path.transition().duration(750).attrTween("d", arcTween); // redraw the arcs
  }
});


function type(d) {
  d.budget_name = d.budget_name;
  d.before_value = +d.before_value;
  d.after_value = +d.after_value;
  return d;
}

// Store the displayed angles in _current.
// Then, interpolate from _current to the new angles.
// During the transition, _current is updated in-place by d3.interpolate.
function arcTween(a) {
  var i = d3.interpolate(this._current, a);
  this._current = i(0);
  return function(t) {
    return arc(i(t));
  };
}
