const display = document.getElementById("display");
const resultDisplay = document.getElementById("result-display");

function showText(text){
    display.innerText += text;
}

function clearOne(){
    display.innerText = display.innerText.slice(0, -1);
}
                        
function clearAll(){
    display.innerText = " ";
    resultDisplay.innerText = " ";
}

function result(){        
    resultDisplay.innerText = eval(display.innerText);
}