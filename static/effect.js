document.addEventListener('DOMContentLoaded', (event) => {
    // Initialize Vanta.js BIRDS effect
    VANTA.BIRDS({
        el: "#vanta-bg",
        mouseControls: true,
        touchControls: true,
        minHeight: 200.00,
        minWidth: 200.00,
        scale: 1.00,
        scaleMobile: 1.00,
        backgroundColor: 0x0, // Background color
        color1: 0xfffff, // Color of the birds
        color2: 0x111111, // Color of the birds
        wingSpan: 0.5, // Wing span of the birds
        separation: 10.00, // Separation between birds
        alignment: 10.00, // Alignment between birds
        cohesion: 190.00, // Cohesion in bird movement
        quantity: 5.0 // Quantity of birds
        // ... other parameters ...
    });

    // Add event listeners for mouseover and mouseout
    document.querySelector('.text-overlay').addEventListener('mouseover', function() {
        this.style.color = '#aqua'; // Change to a different color
    });

    document.querySelector('.text-overlay').addEventListener('mouseout', function() {
        this.style.color = '#ffffff'; // Change back to the original color
    });
});
