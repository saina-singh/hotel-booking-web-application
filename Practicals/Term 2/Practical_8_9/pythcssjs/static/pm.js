function getDate()
{ document.getElementById('demo').innerHTML = Date(); }

function daystoChristmas()
{ 
	
    today = new Date();
    xmas = new Date("December 25, 2021");    
    msPerDay = 24 * 60 * 60 * 1000;
    msLeft = (xmas.getTime() - today.getTime());
    daysLeft = Math.round(msLeft/msPerDay);      
	document.getElementById('demo1').innerHTML = daysLeft + ' Days'; 
}

