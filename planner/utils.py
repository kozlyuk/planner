from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def calculate_page_indexes(current_index, last_index, count=4):
    min_index = 0
    max_index = 0
    # left border
    if current_index - count < 1:
        min_index = 1
    else:
        min_index = current_index - count
    used = current_index - min_index
    left = 2 * count - used
    if current_index + left <= last_index:
        max_index = current_index + left
    else:
        max_index = last_index
    if min_index > 1 and (max_index - min_index) < 2 * count:
        min_index -= 2 * count - (max_index - min_index)
        if min_index < 1:
            min_index = 1
    return [min_index, max_index]


def get_pagination(objects, page, items_count):
    paginator = Paginator(objects, items_count)
    try:
        page_objects = paginator.page(page)
    except PageNotAnInteger:
        page_objects = paginator.page(1)
    except EmptyPage:
        page_objects = paginator.page(1)
    indexes = []
    if paginator.num_pages > 1:
        index_range = calculate_page_indexes(page_objects.number, paginator.num_pages)
        indexes.extend(range(index_range[0], index_range[1] + 1))
    return page_objects, indexes


def get_page_by_list_index(id, ids, per_page_count):
    if id in ids:
        ind = ids.index(id)
        return ind / per_page_count + 1
    else:
        return 1