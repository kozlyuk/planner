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
  vResources: resources,
  vCaptionType: "Resource", // Set to Show Caption : None,Caption,Resource,Duration,Complete,
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
    object_code: {
      title: "Object_code",
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
    taskname: editValue, // if you need to use the this scope, do: editValue.bind(this)
    res: editValue,
    dur: editValue,
    start: editValue,
    end: editValue,
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
  vUseSingleCell: 25000, // Set the threshold cell per table row (Helps performance for large data.
  vFormatArr: ["Day", "Week", "Month", "Quarter"], // Even with setUseSingleCell using Hour format on such a large chart can cause issues in some browsers,
};

const setup = async () => {
  var g = new JSGantt.GanttChart(
    document.getElementById("GanttChartDIV"),
    "day"
  );
  g.addLang("ua", urk_lang);

  data.projects.forEach((el) => {
    g.AddTaskItemObject(createTask(el, g));
  });

  g.setOptions(ganttSettings);
  g.setTotalHeight("99vh");
  g.setShowTaskInfoComp(false);
  g.Draw();
  g.setScrollTo("today");
};

function editValue(list, task, event, cell, column) {
  console.log(event);
  const pk = task.getOriginalID();
  const apiType = task.getGroup() == 1 ? "project" : "task";
  const newValue = event.target.value.trim().replace(" ", "-");
  let fieldName;
  if (!commonProperties[column]) {
    if (column === "pName" && apiType === "project") fieldName = "object_code";
    else fieldName = "part_name";

    if (column === "pRes") fieldName = "executor";
  } else {
    fieldName = commonProperties[column];
  }
  const api_request = `/${apiType}/${pk}/?${fieldName}=${newValue}`;
  console.log(api_request);
  //console.log(list, task, event, cell, column);
  const found = list.find((item) => item.pID == task.getOriginalID());
  if (!found) {
    return;
  } else {
    found[column] = event ? event.target.value : "";
  }
}

function createTask(obj, g) {
  //  gets api project info object
  //  returns object for jsgantt chart

  let newObject = {};
  const isProject = obj.hasOwnProperty("tasks");
  newObject = setCommonPropertiesToGanttObject(obj, newObject);
  newObject.pClass = `task_${obj.exec_status.toLowerCase()}`; //  set custom class for task
  newObject.pComp = 0; //  % of complete
  newObject.pName = isProject ? obj.object_code : obj.part_name;
  newObject.pRes = isProject ? obj.owner : obj.executor;
  newObject.object_code = isProject ? obj.object_code : obj.task;
  newObject.pGroup = isProject ? 1 : 0; //  1 for project task, 0 for task
  newObject.pParent = isProject ? 0 : "";
  newObject.pOpen = 1; //  0 for rendering colapsed projects and tasks
  newObject.pNotes = obj.hasOwnProperty("warning") ? obj.warning : "";
  if (isProject) {
    obj.tasks.forEach((task) => {
      const ganttObj = createTask(task, g);
      ganttObj.pParent = obj.pk; //  set parent id from project
      ganttObj.object_code = obj.object_code;
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

function addInputElementsBySelector(selector) {
  const allSelectorElement = document.querySelectorAll(selector);
  for (let i = 0; i < allSelectorElement?.length; i++) {
    const inputValue = allSelectorElement[i].innerText.trim(); //  take value of input or select
    const child = `&nbsp;&nbsp;<input class="gantt-inputtable" value="${inputValue}">`;
    allSelectorElement[i].innerHTML = child;
  }
}

function afterDrawHandler() {
  console.log("after draw listener");
  hideElementsInputBySelector(".gduration div"); //  hiding inputs in duration column
  hideElementsInputBySelector(".ggroupitem .gresource div"); //  hiding inputs in project resource column
  hideElementsInputBySelector(".gstartdate div, .genddate div"); //  hiding inputs in start and end date columns
  addInputElementsBySelector(".gtaskname.gtaskeditable div span:last-child");
}

function setCommonPropertiesToGanttObject(incomeObject, ganntObject){
  Object.keys(commonProperties).forEach((key) => {
    const dataProperty = commonProperties[key]; //  incoming data key of each object
    if (key === "status") {
      ganntObject[key] = status[incomeObject[dataProperty]]; //  take status value for status collection
      return;
    }
    if (incomeObject.hasOwnProperty(dataProperty) === false) {
      ganntObject[key] = "null";
      return;
    }
    ganntObject[key] = incomeObject[dataProperty]; //  take dynamic key for object from properties of jsgantt value
  });
  return ganntObject;
}

setup();
