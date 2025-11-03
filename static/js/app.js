/**
 * Wheel Analyzer Application JavaScript
 * 
 * Handles dynamic UI updates and component reinitialization
 */

// Reinitialize Flowbite components after HTMX swaps content
document.body.addEventListener('htmx:afterSwap', function(event) {
    // Call Flowbite's initFlowbite() to reinitialize all components in the swapped content
    if (typeof initFlowbite === 'function') {
        initFlowbite();
    }
});
