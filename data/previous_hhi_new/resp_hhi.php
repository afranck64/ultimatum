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
       <h1 align="center" style="color:black"> ACCEPT OR REJECT THE OFFER MADE BY THE PROPOSER! </h1>
       <!--<img src="http://l3s.de/~gadiraju/files/exchange.png" width="225" align="middle"> -->
            <div align="center">
                 <div class="chart" id="piechart" style="opacity: 1;" >
                 </div>
            </div>

     <script type="text/javascript">
          google.charts.load('current', {'packages':['corechart']});
          google.charts.setOnLoadCallback(drawChart);
         
          function drawChart() {
           //console.log("Function Called!");
           responder =Connection failed: No route to host