document.addEventListener("DOMContentLoaded", () => {
    const btn = document.querySelector("button");

    btn.addEventListener("click", () => {
        btn.innerText = "Generating...";
        setTimeout(() => {
            btn.innerText = "Download";
        }, 2000);
    });
});
