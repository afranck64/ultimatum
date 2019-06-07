<!DOCTYPE html>

<html lang='en'>
<head>    
    <link rel="stylesheet" href="style_new.css">
    <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
    <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.4.0/Chart.min.js"></script> -->
    <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
    <title>Ulitmatum Bargaining: The Proposer</title>
</head>
    <body>

<script language="javascript">
(function (global) { 

    if(typeof (global) === "undefined") {
        throw new Error("window is undefined");
    }

    var _hash = "!";
    var noBackPlease = function () {
        global.location.href += "#";

        // making sure we have the fruit available for juice (^__^)
        global.setTimeout(function () {
            global.location.href += "!";
        }, 50);
    };

    global.onhashchange = function () {
        if (global.location.hash !== _hash) {
            global.location.hash = _hash;
        }
    };

    global.onload = function () {            
        noBackPlease();

        // disables backspace on page except on input fields and textarea..
        document.body.onkeydown = function (e) {
            var elm = e.target.nodeName.toLowerCase();
            if (e.which === 8 && (elm !== 'input' && elm  !== 'textarea')) {
                e.preventDefault();
            }
            // stopping event bubbling up the DOM tree..
            e.stopPropagation();
        };          
    }

})(window);
</script>

 <h2 align="center" style="color:#008080"> 
Thank you for your participation in the role of a RESPONDER. <br>You can continue onto your next task as described below.
</h2>

<br>
<br>
<br>

       <h1 align="center" style="color:darkblue"> YOU HAVE NOW BEEN ASSIGNED THE ROLE OF A PROPOSER. <br>PLEASE MAKE A PROPOSAL TO THE RESPONDER! </h1>
<!--<img src="http://l3s.de/~gadiraju/files/exchange.png" width="225" align="middle">
    <img  class="bg" src="https://images.unsplash.com/photo-1447619297994-b829cc1ab44a?ixlib=rb-0.3.5&ixid=eyJhcHBfaWQiOjEyMDd9&s=86ebe4525a7c1d7cfa55148b18741dc5&auto=format&fit=crop&w=1035&q=80">-->
        <br>
        <form action="submit_resp_to_prop.php" method="post" id="prop_hhi">
           <div align="center"> 
            <p align="middle" style="font-size:35px;color:black"> <b>Select Your Proposal From the Dropdown Menu Below:</b> </p> 

 <input type="hidden" name="wid" value="">            

<select id="prop" name="prop" required  onchange="drawChart();fillMessage(); return false">
                <option value="" selected disabled hidden>Choose Here</option>
               <option id="opt1" value="0">0 USD</option>
		 <option id="opt1" value="5">5 CENTS</option>
                <option id="opt1" value="10">10 CENTS</option>
                <option id="opt1" value="15">15 CENTS</option>
                <option id="opt1" value="20">20 CENTS</option>
                <option id="opt1" value="25">25 CENTS</option>
                <option id="opt1" value="30">30 CENTS</option>
                <option id="opt1" value="35">35 CENTS</option>
                <option id="opt1" value="40">40 CENTS</option>
                <option id="opt1" value="45">45 CENTS</option>
                <option id="opt1" value="50">50 CENTS</option>
                <option id="opt1" value="55">55 CENTS</option>
                <option id="opt1" value="60">60 CENTS</option>
                <option id="opt1" value="65">65 CENTS</option>
                <option id="opt1" value="70">70 CENTS</option>
                <option id="opt1" value="75">75 CENTS</option>
                <option id="opt1" value="80">80 CENTS</option>
                <option id="opt1" value="85">85 CENTS</option>
                <option id="opt1" value="90">90 CENTS</option>
                <option id="opt1" value="95">95 CENTS</option>
		<option id="opt1" value="100">1 USD</option>
		<option id="opt1" value="105">1.05 USD</option>
                <option id="opt1" value="110">1.10 USD</option>
                <option id="opt1" value="115">1.15 USD</option>
                <option id="opt1" value="120">1.20 USD</option>
                <option id="opt1" value="125">1.25 USD</option>
                <option id="opt1" value="130">1.30 USD</option>
                <option id="opt1" value="135">1.35 USD</option>
                <option id="opt1" value="140">1.40 USD</option>
                <option id="opt1" value="145">1.45 USD</option>
                <option id="opt1" value="150">1.50 USD</option>
                <option id="opt1" value="155">1.55 USD</option>
                <option id="opt1" value="160">1.60 USD</option>
                <option id="opt1" value="165">1.65 USD</option>
                <option id="opt1" value="170">1.70 USD</option>
                <option id="opt1" value="175">1.75 USD</option>
                <option id="opt1" value="180">1.80 USD</option>
                <option id="opt1" value="185">1.85 USD</option>
                <option id="opt1" value="190">1.90 USD</option>
                <option id="opt1" value="195">1.95 USD</option>
                <option id="opt1" value="200">2 USD</option>


            </select>
        </div>

       <br>

              
            <div align="center"> 
                 <div class="chart" id="piechart" style="opacity: 1;" >
                 </div>
            </div>
     
      <script type="text/javascript">
          google.charts.load('current', {'packages':['corechart']});
          google.charts.setOnLoadCallback(drawChart);
         
          function drawChart() {
           //console.log("Function Called!");
           responder = parseInt(document.getElementById('prop').value);
           proposer = 200-(parseInt(document.getElementById('prop').value));
           
            var data = google.visualization.arrayToDataTable([
              ['Actor', 'Share'],
              ['Proposer', proposer],
              ['Responder', responder]
            ]);
            var options = {
              title: '',    
              'backgroundColor': 'transparent',
              'is3D': 'true',
              legend: {position: 'bottom', textStyle: {fontSize: 18}}
            };
            var chart = new google.visualization.PieChart(document.getElementById('piechart'));
            chart.draw(data, options);
            }
        </script> 

<br> <br>

<script>
function fillMessage() {
  document.getElementById("mesg").innerHTML = "Thank you for your participation in the role of a PROPOSER. <br> You can continue onto your next task as described below.";
}
</script>

<h2 align="center" style="color:#008080" id="mesg"> </h2>



<br> <br>

<hr>

<br> <br>
 <h1 align="center" style="color:#800080"> ON AVERAGE WHAT DO YOU THINK IS THE MINIMUM OFFER THAT OTHER RESPONDERS WOULD ACCEPT?
 <br>PLEASE SELECT YOUR EXPECTATION. </h1>

<br> <br> <br> <br>

<div align="center">
<select id="other_resp" name="other_resp" required >
                <option value="" selected disabled hidden>Choose Here</option>
               <option id="opt1" value="0">0 USD</option>
                 <option id="opt1" value="5">5 CENTS</option>
                <option id="opt1" value="10">10 CENTS</option>
                <option id="opt1" value="15">15 CENTS</option>
                <option id="opt1" value="20">20 CENTS</option>
                <option id="opt1" value="25">25 CENTS</option>
                <option id="opt1" value="30">30 CENTS</option>
                <option id="opt1" value="35">35 CENTS</option>
                <option id="opt1" value="40">40 CENTS</option>
                <option id="opt1" value="45">45 CENTS</option>
                <option id="opt1" value="50">50 CENTS</option>
                <option id="opt1" value="55">55 CENTS</option>
                <option id="opt1" value="60">60 CENTS</option>
                <option id="opt1" value="65">65 CENTS</option>
                <option id="opt1" value="70">70 CENTS</option>
                <option id="opt1" value="75">75 CENTS</option>
                <option id="opt1" value="80">80 CENTS</option>
                <option id="opt1" value="85">85 CENTS</option>
                <option id="opt1" value="90">90 CENTS</option>
                <option id="opt1" value="95">95 CENTS</option>
                <option id="opt1" value="100">1 USD</option>
                <option id="opt1" value="105">1.05 USD</option>
                <option id="opt1" value="110">1.10 USD</option>
                <option id="opt1" value="115">1.15 USD</option>
                <option id="opt1" value="120">1.20 USD</option>
                <option id="opt1" value="125">1.25 USD</option>
                <option id="opt1" value="130">1.30 USD</option>
                <option id="opt1" value="135">1.35 USD</option>
                <option id="opt1" value="140">1.40 USD</option>
                <option id="opt1" value="145">1.45 USD</option>
                <option id="opt1" value="150">1.50 USD</option>
                <option id="opt1" value="155">1.55 USD</option>
                <option id="opt1" value="160">1.60 USD</option>
                <option id="opt1" value="165">1.65 USD</option>
                <option id="opt1" value="170">1.70 USD</option>
                <option id="opt1" value="175">1.75 USD</option>
                <option id="opt1" value="180">1.80 USD</option>
                <option id="opt1" value="185">1.85 USD</option>
                <option id="opt1" value="190">1.90 USD</option>
                <option id="opt1" value="195">1.95 USD</option>
                <option id="opt1" value="200">2 USD</option>
</select>

</div>

<br> <br> <br>

<br> <br>

<hr>

<br> <br>
 <h1 align="center" style="color:#800080"> ON AVERAGE WHAT DO YOU THINK IS THE MINIMUM OFFER THAT OTHER PROPOSERS WOULD MAKE?
 <br>PLEASE SELECT YOUR EXPECTATION. </h1>

<br> <br> <br> <br>

<div align="center">
<select id="other_prop" name="other_prop" required >
                <option value="" selected disabled hidden>Choose Here</option>
               <option id="opt1" value="0">0 USD</option>
                 <option id="opt1" value="5">5 CENTS</option>
                <option id="opt1" value="10">10 CENTS</option>
                <option id="opt1" value="15">15 CENTS</option>
                <option id="opt1" value="20">20 CENTS</option>
                <option id="opt1" value="25">25 CENTS</option>
                <option id="opt1" value="30">30 CENTS</option>
                <option id="opt1" value="35">35 CENTS</option>
                <option id="opt1" value="40">40 CENTS</option>
                <option id="opt1" value="45">45 CENTS</option>
                <option id="opt1" value="50">50 CENTS</option>
                <option id="opt1" value="55">55 CENTS</option>
                <option id="opt1" value="60">60 CENTS</option>
                <option id="opt1" value="65">65 CENTS</option>
                <option id="opt1" value="70">70 CENTS</option>
                <option id="opt1" value="75">75 CENTS</option>
                <option id="opt1" value="80">80 CENTS</option>
                <option id="opt1" value="85">85 CENTS</option>
                <option id="opt1" value="90">90 CENTS</option>
                <option id="opt1" value="95">95 CENTS</option>
                <option id="opt1" value="100">1 USD</option>
                <option id="opt1" value="105">1.05 USD</option>
                <option id="opt1" value="110">1.10 USD</option>
                <option id="opt1" value="115">1.15 USD</option>
                <option id="opt1" value="120">1.20 USD</option>
                <option id="opt1" value="125">1.25 USD</option>
                <option id="opt1" value="130">1.30 USD</option>
                <option id="opt1" value="135">1.35 USD</option>
                <option id="opt1" value="140">1.40 USD</option>
                <option id="opt1" value="145">1.45 USD</option>
                <option id="opt1" value="150">1.50 USD</option>
                <option id="opt1" value="155">1.55 USD</option>
                <option id="opt1" value="160">1.60 USD</option>
                <option id="opt1" value="165">1.65 USD</option>
                <option id="opt1" value="170">1.70 USD</option>
                <option id="opt1" value="175">1.75 USD</option>
                <option id="opt1" value="180">1.80 USD</option>
                <option id="opt1" value="185">1.85 USD</option>
                <option id="opt1" value="190">1.90 USD</option>
                <option id="opt1" value="195">1.95 USD</option>
                <option id="opt1" value="200">2 USD</option>

</select>

</div>

<br> <br> <br>
                                                                        
          <div align="center">
            <button type="submit" value="Submit" align="middle">Submit</button>
           </div>

          </form>
    </body>
</html>
