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

    // 4. Поиск и фильтрация списка тематик по словам при создании и редактировании обращения
    const topicSelect = document.getElementById('topic_id');
    const topicSearch = document.getElementById('topic_search');
    const topicSearchClear = document.getElementById('topic_search_clear');
    const topicSearchCount = document.getElementById('topic_search_count');

    if (topicSelect && topicSearch) {
        // Кешируем исходный список вариантов
        const allTopicOptions = [];
        for (let i = 0; i < topicSelect.options.length; i++) {
            const opt = topicSelect.options[i];
            allTopicOptions.push({
                value: opt.value,
                text: opt.textContent.trim(),
                selected: opt.selected
            });
        }

        const totalTopicsCount = allTopicOptions.filter(o => o.value !== '').length;
        if (topicSearchCount) {
            topicSearchCount.textContent = `Всего: ${totalTopicsCount}`;
        }

        function filterTopics() {
            const query = topicSearch.value.trim().toLowerCase();
            const words = query ? query.split(/\s+/).filter(Boolean) : [];
            const currentSelectedVal = topicSelect.value;

            const placeholder = allTopicOptions.find(o => o.value === '');
            const items = allTopicOptions.filter(o => o.value !== '');

            // Все введенные пользователем слова должны входить в название тематики (в любом порядке)
            const matchedItems = items.filter(item => {
                if (words.length === 0) return true;
                const lowerText = item.text.toLowerCase();
                return words.every(word => lowerText.includes(word));
            });

            // Пересобираем выпадающий список
            topicSelect.innerHTML = '';
            if (placeholder) {
                const pOpt = document.createElement('option');
                pOpt.value = placeholder.value;
                pOpt.textContent = placeholder.text;
                topicSelect.appendChild(pOpt);
            }

            let matchFoundForCurrent = false;
            matchedItems.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.value;
                opt.textContent = item.text;
                if (item.value === currentSelectedVal) {
                    opt.selected = true;
                    matchFoundForCurrent = true;
                }
                topicSelect.appendChild(opt);
            });

            // Если текущее выбранное значение не входит в отфильтрованный список
            if (!matchFoundForCurrent) {
                if (matchedItems.length === 1 && words.length > 0) {
                    // Если совпадение ровно одно, автоматически выбираем его
                    topicSelect.value = matchedItems[0].value;
                } else if (words.length > 0 && placeholder) {
                    topicSelect.value = '';
                }
            }

            // Обновляем индикатор количества найденных записей
            if (topicSearchCount) {
                if (words.length > 0) {
                    topicSearchCount.textContent = `Найдено: ${matchedItems.length} из ${items.length}`;
                    topicSearchCount.className = matchedItems.length === 0 ? 'text-danger fw-bold' : 'text-primary fw-bold';
                } else {
                    topicSearchCount.textContent = `Всего: ${items.length}`;
                    topicSearchCount.className = 'text-muted';
                }
            }
        }

        topicSearch.addEventListener('input', filterTopics);

        // Предотвращаем случайную отправку всей формы при нажатии Enter в строке поиска
        topicSearch.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                topicSelect.focus();
            } else if (e.key === 'Escape') {
                topicSearch.value = '';
                filterTopics();
            }
        });

        if (topicSearchClear) {
            topicSearchClear.addEventListener('click', function () {
                topicSearch.value = '';
                filterTopics();
                topicSearch.focus();
            });
        }
    }

    // 5. Взаимоисключение чекбоксов обслуживания ("Не состоит" и "Состоит в НКО")
    const notServicedCheckbox = document.getElementById('not_serviced');
    const servicedInNkoCheckbox = document.getElementById('serviced_in_nko');

    if (notServicedCheckbox && servicedInNkoCheckbox) {
        notServicedCheckbox.addEventListener('change', function () {
            if (this.checked) {
                servicedInNkoCheckbox.checked = false;
            }
        });
        servicedInNkoCheckbox.addEventListener('change', function () {
            if (this.checked) {
                notServicedCheckbox.checked = false;
            }
        });
    }
});
