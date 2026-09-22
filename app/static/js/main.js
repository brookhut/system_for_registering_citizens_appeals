// Citizens Appeals Management System - Main JS

document.addEventListener('DOMContentLoaded', function () {
    // 1. Clickable table rows: clicking a row navigates to appeal card
    const clickableRows = document.querySelectorAll('.clickable-row');
    clickableRows.forEach(row => {
        row.addEventListener('click', function (e) {
            // Ignore if clicked on an anchor, button, input, or inside them
            if (e.target.closest('a') || e.target.closest('button') || e.target.closest('input')) {
                return;
            }
            const href = this.getAttribute('data-href');
            if (href) {
                window.location.href = href;
            }
        });
    });

    // 2. Cascading dropdowns: Management -> District and Plot
    // "в Управление может входить несколько округов, в управление может входить несколько участков"
    const managementSelect = document.getElementById('management_id');
    const districtSelect = document.getElementById('district_id');
    const plotSelect = document.getElementById('plot_id');

    if (managementSelect && districtSelect && plotSelect) {
        let relationsCache = null;

        // Fetch management relations
        fetch('/api/management-relations')
            .then(res => res.json())
            .then(data => {
                relationsCache = data;
                // If management is already selected, apply filter
                if (managementSelect.value) {
                    updateLinkedDropdowns(managementSelect.value);
                }
            })
            .catch(err => console.error('Error fetching management relations:', err));

        managementSelect.addEventListener('change', function () {
            if (relationsCache) {
                updateLinkedDropdowns(this.value);
            }
        });

        function updateLinkedDropdowns(managementId) {
            if (!managementId || !relationsCache || !relationsCache[managementId]) {
                // No management chosen: show all options
                resetDropdownOptions(districtSelect);
                resetDropdownOptions(plotSelect);
                return;
            }

            const info = relationsCache[managementId];
            const linkedDistricts = info.district_ids || [];
            const linkedPlots = info.plot_ids || [];

            filterSelect(districtSelect, linkedDistricts, 'Округ из выбранного управления');
            filterSelect(plotSelect, linkedPlots, 'Участок из выбранного управления');
        }

        function filterSelect(selectElem, allowedIds, groupLabel) {
            const currentValue = selectElem.value;
            const options = Array.from(selectElem.querySelectorAll('option'));

            // If no linked items configured for this management, keep all options available
            if (!allowedIds || allowedIds.length === 0) {
                return;
            }

            let currentStillAvailable = false;
            options.forEach(opt => {
                if (!opt.value) return; // empty placeholder
                const optId = parseInt(opt.value, 10);
                if (allowedIds.includes(optId)) {
                    opt.hidden = false;
                    opt.disabled = false;
                    if (opt.value === currentValue) currentStillAvailable = true;
                } else {
                    opt.hidden = true;
                    opt.disabled = true;
                }
            });

            // If currently selected option is now hidden, reset to empty
            if (currentValue && !currentStillAvailable) {
                // Only reset if select is not disabled (i.e. we are editing, but wait, don't break valid selections)
                selectElem.value = '';
            }
        }

        function resetDropdownOptions(selectElem) {
            const options = selectElem.querySelectorAll('option');
            options.forEach(opt => {
                opt.hidden = false;
                opt.disabled = false;
            });
        }
    }

    // 3. Date registration validation on client side
    // Cannot be greater than current date (DD.MM.YYYY)
    const regDateInput = document.getElementById('reg_date');
    if (regDateInput) {
        regDateInput.addEventListener('change', function () {
            const selectedDate = new Date(this.value);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            if (selectedDate > today) {
                alert('Дата регистрации не может быть больше текущей даты!');
                // Reset to today
                const yyyy = today.getFullYear();
                const mm = String(today.getMonth() + 1).padStart(2, '0');
                const dd = String(today.getDate()).padStart(2, '0');
                this.value = `${yyyy}-${mm}-${dd}`;
            }
        });
    }
});
