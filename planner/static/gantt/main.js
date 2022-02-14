const commonProperties = {
  pID: "pk",
  pStart: "start_date",
  pEnd: "finish_date",
  pPlanStart: "planned_start",
  pPlanEnd: "planned_finish",
  status: "exec_status",
};

const urk_lang = {
  january: "Січень",
  february: "Лютий",
  march: "Березень",
  april: "Квітень",
  maylong: "Травень",
  june: "Червень",
  july: "Липень",
  august: "Серпень",
  september: "Вересень",
  october: "Жовтень",
  november: "Листопад",
  december: "Грудень",
  jan: "Січ",
  feb: "Лют",
  mar: "Берез",
  apr: "Квіт",
  may: "Трав",
  jun: "Черв",
  jul: "Лип",
  aug: "Серп",
  sep: "Верес",
  oct: "Жовт",
  nov: "Лист",
  dec: "Груд",
  sunday: "Неділя",
  monday: "Понеділок",
  tuesday: "Вівторок",
  wednesday: "Середа",
  thursday: "Четвер",
  friday: "П'ятниця",
  saturday: "Субота",
  sun: "	Нд",
  mon: "	Пн",
  tue: "	Вт",
  wed: "	Ср",
  thu: "	Чт",
  fri: "	Пт",
  sat: "	Сб",
  resource: "Виконавець",
  duration: "Тривалість",
  comp: "% виконання",
  completion: "Виконано",
  startdate: "Поч. дата",
  planstartdate: "План. поч. дата",
  enddate: "Кін. дата",
  planenddate: "План. кін. дата",
  cost: "Cost",
  moreinfo: "Деталі",
  notes: "Подробиці",
  format: "Формат",
  hour: "Година",
  day: "День",
  week: "Тиждень",
  month: "Місяць",
  quarter: "Квартал",
  hours: "Годин",
  days: "Днів",
  weeks: "Тижнів",
  months: "Місяців",
  quarters: "Кварталів",
  hr: "год.",
  dy: "дн.",
  wk: "тиж.",
  mth: "міс.",
  qtr: "кв.",
  hrs: "год.",
  dys: "дн.",
  wks: "тиж.",
  mths: "міс.",
  qtrs: "кв.",
  tooltipLoading: "Завантаження...",
};

const status = {
  IW: "В черзі",
  IP: "Виконується",
  OC: "На перевірці",
  HD: "Виконано",
  ST: "Надіслано",
  OH: "Призупинено",
  CL: "Відмінено",
};

const ganttSettings = {
  vCaptionType: "Caption", // Set to Show Caption : None,Caption,Resource,Duration,Complete,
  vHourColWidth: 16,
  vDayColWidth: 32,
  vWeekColWidth: 64,
  vMonthColWidth: 128,
  vQuarterColWidth: 256,
  vTooltipDelay: 1000,
  vDateTaskDisplayFormat: "day dd month yyyy", // Shown in tool tip box
  vDayMajorDateDisplayFormat: "mon yyyy - Week ww", // Set format to dates in the "Major" header of the "Day" view
  vWeekMinorDateDisplayFormat: "dd mon", // Set format to display dates in the "Minor" header of the "Week" view
  vLang: "ua",
  vShowTaskInfoLink: 0, // Show link in tool tip (0/1)
  vShowEndWeekDate: 0, // Show/Hide the date for the last day of the week in header for daily
  vAdditionalHeaders: {
    // Add data columns to your table
    status: {
      title: "Статус",
    },
  },
  vEvents: {
    // taskname: console.log,
    // res: console.log,
    // start: console.log,
    // end: console.log,
    // planstart: console.log,
    // planend: console.log,
    beforeDraw: () => console.log("before draw listener"),
    afterDraw: afterDrawHandler,
  },
  vEventsChange: {
    // taskname: editValue, // if you need to use the this scope, do: editValue.bind(this)
    // res: editValue,
    // dur: editValue,
    // start: editValue,
    // end: editValue,
    planstart: editValue,
    planend: editValue,
  },
  vEditable: true,
  vUseSort: true,
  vShowCost: false,
  vShowRes: data?.view_mode == "project_view" ? 1 : 0,
  vShowAddEntries: false,
  vShowComp: false,
  vShowPlanStartDate: true,
  vShowPlanEndDate: true,
  vUseSingleCell: 35000, // Set the threshold cell per table row (Helps performance for large data.
  vFormatArr: ["Day", "Week", "Month", "Quarter"], // Even with setUseSingleCell using Hour format on such a large chart can cause issues in some browsers,
};

const setup = async () => {
  var g = new JSGantt.GanttChart(
    document.getElementById("GanttChartDIV"),
    "day"
  );
  const ganttSettings = {
    vCaptionType: "Caption", // Set to Show Caption : None,Caption,Resource,Duration,Complete,
    vHourColWidth: 16,
    vDayColWidth: 32,
    vWeekColWidth: 64,
    vMonthColWidth: 128,
    vQuarterColWidth: 256,
    vTooltipDelay: 1000,
    vDateTaskDisplayFormat: "DAY dd month yyyy", // Shown in tool tip box
    vDayMajorDateDisplayFormat: "mon yyyy - Week ww", // Set format to dates in the "Major" header of the "Day" view
    vWeekMinorDateDisplayFormat: "dd mon", // Set format to display dates in the "Minor" header of the "Week" view
    vLang: "ua",
    vShowTaskInfoLink: 0, // Show link in tool tip (0/1)
    vShowEndWeekDate: 0, // Show/Hide the date for the last day of the week in header for daily
    vAdditionalHeaders: {
      // Add data columns to your table
      status: {
        title: "Статус",
      },
    },
    vEvents: {
      beforeDraw: () => console.log("before draw listener"),
      afterDraw: () => afterDrawHandler(g),
    },
    vEventsChange: {
      planstart: editValue,
      planend: editValue,
    },
    vUseSort: true,
    vShowCost: false,
    vShowRes: data?.view_mode == "project_view" ? 1 : 0,
    vShowAddEntries: false,
    vShowComp: false,
    vShowPlanStartDate: true,
    vShowPlanEndDate: true,
    vUseSingleCell: 35000, // Set the threshold cell per table row (Helps performance for large data.
    vFormatArr: ["Day", "Week", "Month", "Quarter"], // Even with setUseSingleCell using Hour format on such a large chart can cause issues in some browsers,
  };

  g.addLang("ua", urk_lang);
  g.setOptions(ganttSettings);

  data.projects.forEach((el) => {
    g.AddTaskItemObject(createTask(el, g));
  });
  g.setTotalHeight("92vh");
  g.setShowTaskInfoComp(false);
  g.setScrollTo("today");
  g.Draw();
};

function getCookie(name) {
  if (!document.cookie) {
    return null;
  }

  const xsrfCookies = document.cookie.split(';')
    .map(c => c.trim())
    .filter(c => c.startsWith(name + '='));

  if (xsrfCookies.length === 0) {
    return null;
  }
  return decodeURIComponent(xsrfCookies[0].split('=')[1]);
}

function editValue(list, task, event, cell, column) {
  console.log(list, task, event, cell, column);
  const pk = task.getOriginalID();
  const apiType = task.getGroup() == 1 ? "project" : "task";
  const newValue = event.target.value.trim();
  let fieldName = (column === "pPlanStart") ? "planned_start" : "planned_finish";
  var formData = new FormData();
  formData.append("pk", pk);
  formData.append(fieldName, newValue);
  formData.append("task_type", apiType);
  editPostRequest(formData);
  const found = list.find((item) => item.pID == task.getOriginalID());
  if (!found) {
    return;
  } else {
    found[column] = event ? event.target.value : "";
  }
}

function editPostRequest(object){
  const csrfToken = getCookie('csrftoken');
  fetch("change/", {
    method: 'POST',
    body: object,
    headers: {
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
}

function createTask(obj, g) {
  //  gets api project info object
  //  returns object for jsgantt chart

  let newObject = {};
  const isProject = obj.hasOwnProperty("tasks");
  newObject = setCommonPropertiesToGanttObject(obj, newObject);
  newObject.pClass = `task_${obj.exec_status.toLowerCase()}`; //  set custom class for task
  newObject.pComp = 0; //  % of complete
  newObject.pName = isProject ? obj.object_code : obj.subtask;
  newObject.pRes = isProject ? obj.owner : obj.executor;
  newObject.pGroup = isProject ? 1 : 0; //  1 for project task, 0 for task
  newObject.pParent = isProject ? 0 : "";
  newObject.pOpen = 1; //  0 for rendering colapsed projects and tasks
  newObject.pCaption = isProject ? obj.object_code : obj.subtask;
  if (isProject) {
    obj.tasks.forEach((task) => {
      const ganttObj = createTask(task, g);
      ganttObj.pParent = obj.pk; //  set parent id from project
      g.AddTaskItemObject(ganttObj);
    });
  }

  return newObject;
}

function hideElementsInputBySelector(selector) {
  const allSelectorElement = document.querySelectorAll(selector);
  for (let i = 0; i < allSelectorElement?.length; i++) {
    const inputValue = allSelectorElement[i].firstChild.value; //  take value of input or select
    allSelectorElement[i].firstChild.remove(); //  delete node
    allSelectorElement[i].innerHTML = inputValue; //  paste value of input or select into div
  }
}

function hideInputsFromTaskName(selector) {
  const allSelectorElement = document.querySelectorAll(selector);
  for (let i = 0; i < allSelectorElement?.length; i++) {
    const inputValue =
      "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;" +
      allSelectorElement[i].lastChild.value; //  take value of input or select
    allSelectorElement[i].lastChild.remove(); //  delete node
    allSelectorElement[i].innerHTML = inputValue; //  paste value of input or select into div
  }
}

function afterDrawHandler(g) {
  console.log("after draw listener");
  addingEditProjectLink(".ggroupitem .gtaskname div:first-child");
  addingEditingInputToPlanDates(".gplanstartdate div, .gplanenddate div", g)
}

function setCommonPropertiesToGanttObject(incomeObject, ganntObject) {
  Object.keys(commonProperties).forEach((key) => {
    const dataProperty = commonProperties[key]; //  incoming data key of each object
    if (key === "status") {
      ganntObject[key] = status[incomeObject[dataProperty]]; //  take status value for status collection
      return;
    }
    if (incomeObject.hasOwnProperty(dataProperty) === false) {
      ganntObject[key] = null;
      return;
    }
    ganntObject[key] = incomeObject[dataProperty]; //  take dynamic key for object from properties of jsgantt value
  });

  if (incomeObject.start_date === "None") {
    ganntObject.pStart = null;
  }
  if(incomeObject.finish_date === "None"){
    ganntObject.pEnd = null;
  }
  if (incomeObject.planned_start === "None") {
    ganntObject.pPlanStart = " ";
  }
  return ganntObject;
}

function swapStatusDuringColumns() {
  const duringColumnSelector = ".gduration";
  const statusColumnSelector = ".gadditional.gadditional-status";
  const allStatusCells = document.querySelectorAll(statusColumnSelector);
  const allDuringCells = document.querySelectorAll(duringColumnSelector);
  for (let i = 0; i < allDuringCells.length; i++) {
    const nextToDuring = allDuringCells[i].nextSibling;
    const prevToStatus = allStatusCells[i].previousSibling;
    prevToStatus.after(allDuringCells[i]);
    nextToDuring.before(allStatusCells[i]);
  }
}

function addingEditProjectLink(selector) {
  const items = document.querySelectorAll(selector);
  items.forEach((item) => {
    const pk = item.lastChild.getAttribute("pk");
    const wrapper = document.createElement("a");
    wrapper.classList.add("edit_project_link");
    wrapper.setAttribute("target", "_blank");
    wrapper.setAttribute("href", `/project/${pk}/change`);
    wrapper.innerHTML = `<i style="font-size: 16px;" data-toggle="tooltip" title="" data-placement="right" class="far fa-sticky-note" data-original-title="Відкрити редагування проекту"></i>`;
    item.appendChild(wrapper);
  });
}

function addingEditingInputToPlanDates(selector, g){
  const nodes = document.querySelectorAll(selector);
  nodes.forEach(node => {
    const nodeValueArr = node.innerText.split("/");
    const nodeValue = `${nodeValueArr[2]}-${nodeValueArr[1]}-${nodeValueArr[0]}`;
    const input = document.createElement("input");
    input.setAttribute("type", "date");
    input.setAttribute("class", "gantt-inputtable");
    input.setAttribute("value", nodeValue);
    node.innerText = "";
    node.appendChild(input);
    const id = node.parentNode.parentNode.getAttribute("id").split("_")[1];
    const columnName = node.parentNode.getAttribute("class").replace("g", " ").replace("date", " ").trim();
    g.addListenerInputCellCustom(node.parentNode, columnName, g.vEventsChange, g.getEventsClickCell(), g.getList(), g.getArrayLocationByID(id));
  });
}

setup();
