document.addEventListener("DOMContentLoaded", () => {

    const customBtn = document.querySelector(".accessibility-button");

    // When your navbar button is clicked
    customBtn.addEventListener("click", () => {
        const siennaBtn = document.querySelector(".asw-menu-btn");

        if (siennaBtn) {
            siennaBtn.click(); // triggers Sienna panel
        }
    });

    // 🔥 Hide the default floating button
    const hideDefault = () => {
        const siennaBtn = document.querySelector(".asw-menu-btn");

        if (siennaBtn) {
            siennaBtn.style.display = "none";
        } else {
            setTimeout(hideDefault, 100);
        }
    };

    hideDefault();
});