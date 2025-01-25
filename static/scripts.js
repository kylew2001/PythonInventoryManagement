// Ensure the script is executed only if the page is menu.html
if (document.getElementById('menuModal')) {
    // Toggle Menu Modal
    function toggleMenu() {
        const menuModal = document.getElementById('menuModal');
        if (menuModal) {
            if (menuModal.style.display === 'flex') {
                menuModal.style.display = 'none';
                body.classList.remove('modal-active'); // Remove class to restore opacity

            } else {
                menuModal.style.display = 'flex';
                body.classList.add('modal-active'); // Add class to reduce opacity of table

            }
        }
    }

    // Add Event Listener for the "X" close button in the menu modal
    document.addEventListener('DOMContentLoaded', () => {
        // Close the menu modal when clicking the "X" button
        const closeMenuButton = document.querySelector('.menu-modal .close');
        if (closeMenuButton) {
            closeMenuButton.addEventListener('click', () => {
                const menuModal = document.getElementById('menuModal');
                if (menuModal) menuModal.style.display = 'none';
                document.body.classList.remove('modal-active'); // Reset opacity when closing menu

            });
        }

        // Close the menu modal when clicking outside the modal
        window.addEventListener('click', (event) => {
            const menuModal = document.getElementById('menuModal');
            if (menuModal && event.target === menuModal) {
                menuModal.style.display = 'none';
                document.body.classList.remove('modal-active'); // Reset opacity

            }
        });

        // Ensure the menu modal is hidden on page load
        const menuModal = document.getElementById('menuModal');
        const orderModal = document.getElementById('orderModal');
        if (menuModal) menuModal.style.display = 'none';
        if (orderModal) orderModal.style.display = 'none';
    });
    // Ensure the order modal is hidden on page load



}
