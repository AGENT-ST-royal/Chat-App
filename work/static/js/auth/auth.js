const password = document.getElementById("password");
const check = document.getElementById("check");

 function change(){
    if (password.type === 'password'){
        password.type = 'text';
        check.classList.replace('bx-hide', 'bx-show')
    } else {
        password.type = 'password';
        check.classList.replace('bx-show', 'bx-hide')
    }
}