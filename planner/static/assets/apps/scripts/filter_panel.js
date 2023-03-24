document.addEventListener("DOMContentLoaded", () => {
    function filterState() {
        const state = localStorage.getItem('filter_state');
        return state;
    };
    function setFilterState(state) {
        localStorage.setItem('filter_state', state)
    }
    // if (filterState() == 'True') {
    //     $('.filter-panel').toggleClass('open');
    // }
    $('.filter-panel .theme_btn, .filter-panel .mobile-close').on('click', function() {
        $('.filter-panel').toggleClass('open');
        if (filterState() == null) {
            setFilterState('True')
        } else if (filterState() == 'True') {
            setFilterState('False')
        } else if (filterState() == 'False') {
            setFilterState('True')
        }
    });
});
