function daystoChristmas()
{ 

    today = new Date();
    window.alert("Today's date is: " + today);
    xmas = new Date("December 25, 2022");    
    msPerDay = 24 * 60 * 60 * 1000;
    msLeft = (xmas.getTime() - today.getTime());
    daysLeft = Math.round(msLeft/msPerDay);      
	document.getElementById('demo1').innerHTML = daysLeft + " Days left until next Christmas"; 
}

function userdatetodaystoChristmas()
{ 

	datebyuser = document.getElementById('userdate1').value; 
    userdate = new Date(datebyuser);
    window.alert("User entered the date: " + userdate);
    xmas = new Date("December 25, 2022");    
    msPerDay = 24 * 60 * 60 * 1000;
    msLeft = (xmas.getTime() - userdate.getTime());
    daysLeft = Math.round(msLeft/msPerDay);      
	document.getElementById('demo2').innerHTML = daysLeft + " Days left until next Christmas from user date"; 
}