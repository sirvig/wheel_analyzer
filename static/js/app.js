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

    // Close edit notes modal after successful note update
    // Check if the swap target is a notes-display element (ID pattern: notes-display-{pk})
    if (event.detail.target && event.detail.target.id && event.detail.target.id.startsWith('notes-display-')) {
        const modal = document.getElementById('edit-notes-modal');
        if (modal && typeof hideEditNotesModal === 'function') {
            hideEditNotesModal();
        }
    }
});
