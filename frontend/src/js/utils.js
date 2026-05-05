import "jquery";
import "jquery-validation";
import "seedrandom";
import "@dashboardcode/bsmultiselect";
import jsPsych from "jspsych";
import Mustache from "mustache";
import Bowser from "bowser";


export function getWorkerInfo() {
  // check for prolific, mturk, or connect status from the jspsych.turk module
  let platform = "turk";
  const is_prolific = _.some(Object.values(jsPsych.turk.prolificInfo()));
  const is_turk = _.some(Object.values(jsPsych.turk.turkInfo()));
  const is_connect = _.some(Object.values(jsPsych.turk.connectInfo()));

  let info;

  if (is_prolific) {
    info = jsPsych.turk.prolificInfo();
    platform = "prolific";

    return { ...info, platform };
  }
  if (is_turk || is_connect) {

    // differentiate between the two
    if (_.some(Object.values(jsPsych.turk.turkInfo()))) {
      info = jsPsych.turk.turkInfo();
      platform = "turk";
    }

    if (_.every(Object.values(jsPsych.turk.connectInfo()))) {
      info = jsPsych.turk.connectInfo();
      platform = "connect";
    }

    return { ...info, platform };

  }

  // No platform detected — generate a direct-access participant ID
  let participantId = localStorage.getItem("direct_participant_id");
  if (!participantId) {
    participantId = "direct_" + Math.random().toString(36).substring(2, 10) + "_" + Date.now();
    localStorage.setItem("direct_participant_id", participantId);
  }
  return { workerId: participantId, assignmentId: "direct", hitId: "direct", platform: "direct" };
}

export async function getExperimentInfo({ worker_info }) {
  if (worker_info.platform === "prolific") {
    worker_info = {
      worker_id: worker_info.PROLIFIC_PID,
      hit_id: worker_info.STUDY_ID,
      assignment_id: worker_info.SESSION_ID,
      platform: worker_info.platform
    };
  } else if (worker_info.platform === "turk") {
    worker_info = {
      worker_id: worker_info.workerId,
      hit_id: worker_info.hitId,
      assignment_id: worker_info.assignmentId,
      platform: worker_info.platform
    };
  } else if (worker_info.platform === "connect") {
    worker_info = {
      worker_id: worker_info.participantId,
      hit_id: worker_info.projectId,
      assignment_id: worker_info.assignmentId,
      platform: worker_info.platform
    };
  } else if (worker_info.platform === "direct") {
    worker_info = {
      worker_id: worker_info.workerId,
      hit_id: worker_info.hitId,
      assignment_id: worker_info.assignmentId,
      platform: worker_info.platform
    };
  }

  const urlCondition = getUrlParameter("condition");
  if (urlCondition) {
    worker_info.condition = urlCondition;
  }

  const response = await fetch("/init", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(worker_info), // body data type must match "Content-Type" header
  });
  if (!response.ok) {
    const message = `An error has occured: ${response.status}`;
    throw new Error(message);
  }
  const json_response = await response.json();
  console.log("json_resp", json_response);

  return json_response;
}


export function confirmExit() {
  return "You have attempted to leave this page. Are you sure?";
}

export function addTrialTypeDependencies(dependencies, trial_types) {
  for (const dependency of dependencies) {
    if (
      trial_types.filter((t) => t.info.name === dependency.info.name).length ===
      0
    ) {
      trial_types.push(dependency);
    }
  }
  return trial_types;
}

export function countPageRefreshes() {
  let refresh_count = parseInt(localStorage.getItem("refresh_count"));
  if (isNaN(refresh_count)) {
    refresh_count = 0;
  } else {
    refresh_count++;
  }
  localStorage.setItem("refresh_count", refresh_count.toString());
  return refresh_count;
}

export function countInstructionsViewed() {
  let instructions_viewed_count = parseInt(
    localStorage.getItem("instructions_viewed_count"),
  );
  if (isNaN(instructions_viewed_count)) {
    instructions_viewed_count = 0;
  } else {
    instructions_viewed_count++;
  }
  localStorage.setItem(
    "instructions_viewed_count",
    instructions_viewed_count.toString(),
  );
  return instructions_viewed_count;
}

export function getCondition(condition_list) {
  let condition = localStorage.getItem("condition");
  if (!condition || !condition_list.includes(condition)) {
    condition = _.sample(condition_list);
    localStorage.setItem("condition", condition);
  }
  return condition;
}

export async function wait(func, ms) {
  return new Promise((resolve) => {
    setTimeout(function () {
      resolve(func());
    }, ms);
  });
}

export async function isBrowserSupported() {
  const tags = ["[[", "]]"];
  const browser = Bowser.getParser(window.navigator.userAgent);
  const is_valid_browser = browser.satisfies({
    chrome: ">=67",
    edge: ">=17",
    firefox: ">=60",
    safari: ">=11.1",
  });
  const is_mobile =
    browser.getPlatformType() === "mobile" ||
    browser.getPlatformType() === "tablet";
  console.log("is_mobile", is_mobile);
  console.log("is_valid_browser", is_valid_browser);
  console.log("platform", browser.getPlatformType());
  if (!is_valid_browser || is_mobile) {
    let error_text;
    if (!is_valid_browser) {
      error_text = `Hey there, it looks like
      you're using an old or unsupported browser.
      You can't access this particular test with
      your browser because it is not compatible
      with our standards and/or security for your data.
      <a href="https://www.google.com/chrome/" target="_blank">
      Click here</a>
      to download a free supported browser, then
      access the test again from there.
      Thanks!`;
    } else if (is_mobile) {
      error_text = `Hey there, it looks like
      you're using a mobile device.
      You can't access this particular test
      from mobile devices at this time.
      Please access the test from a desktop
      or laptop computer, on an up-to-date
      web browser, like Google Chrome.
      Thanks!`;
    }
    const render_data = {
      error: error_text,
    };
    try {
      const response = await fetch("src/html/error.html");
      const template = await response.text();
      const rendered_template = Mustache.render(
        template,
        render_data,
        {},
        tags,
      );
      $("html").addClass("max-size"); // to center content
      $("body").addClass("jspsych-display-element max-size"); // to center content
      $("body").append(rendered_template);
    } catch (err) {
      alert(error_text);
      console.error(err);
    }
    return false;
  }
  return true;
}

export function rearrangeArray(arr, index) {
  // Rearrange the array given a set of indexes
  return index.map((i) => arr[i]);
}

export function getUrlParameter(name) {
  name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
  var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
  var results = regex.exec(location.search);
  return results === null
    ? ""
    : decodeURIComponent(results[1].replace(/\+/g, " "));
}

export function insertInteractionData(json_data) {
  let exp_data = JSON.parse(json_data);
  exp_data.forEach(function (x) {
    delete x.internal_node_id;
  });
  // grab the browser interaction data
  let interaction_data = JSON.parse(jsPsych.data.getInteractionData().json());
  // attach the latter to the former (merged on trial index)
  for (const exp_data_row of exp_data) {
    const interaction_events = [];
    for (const interaction_data_row of interaction_data) {
      if (exp_data_row.trial_index === interaction_data_row.trial) {
        delete interaction_data_row.trial;
        interaction_events.push(interaction_data_row);
      }
    }
    exp_data_row.browser_events = interaction_events;
  }
  return exp_data;
}

export async function generateInstructionsWithMustache({
  pages = [`<p>XXX</p>`],
  tags = ["{{", "}}"],
  post_trial_gap = 500,
  reading_speed_button_delay_type = "enable",
  reading_speed = 250,
}) {
  const rendered_instructions = await Promise.all(
    _.map(pages, async (page) => {
      const render_data = {
        instructions: page,
      };
      const response = await fetch("src/html/instructions.html");
      const template = await response.text();
      return Mustache.render(template, render_data, {}, tags);
    }),
  );
  const instructions = {
    type: "instructions",
    pages: rendered_instructions,
    show_clickable_nav: true,
    post_trial_gap,
    reading_speed_button_delay_type,
    reading_speed,
  };
  return instructions;
}

export function generateInstructions({
  pages = [`<p>XXX</p>`],
  iti = 500,
  tags = ["{{", "}}"],
}) {
  let instructions = [];
  for (const page of pages) {
    const this_instructions_trial = {
      type: "render-mustache-template",
      url: "src/html/instructions.html",
      cont_btn: "continueButton",
      post_trial_gap: iti,
      data: {
        experiment_phase: "instructions",
      },
      render_data: {
        instructions: page,
      },
      tags,
    };
    instructions.push(this_instructions_trial);
  }
  return instructions;
}

export function getClosestValue(goal, arr) {
  // Get the closest value to goal from an array, arr.
  let curr = arr[0];
  for (const val of arr) {
    if (Math.abs(goal - val) < Math.abs(goal - curr)) {
      curr = val;
    }
  }
  return curr;
}

export function getFrameRate() {
  const times = [];
  let fps;

  function refreshLoop() {
    window.requestAnimationFrame(() => {
      const now = performance.now();
      while (times.length > 0 && times[0] <= now - 1000) {
        times.shift();
      }
      times.push(now);
      fps = times.length;
      refreshLoop();
    });
  }

  refreshLoop();

  return new Promise(function (resolve, reject) {
    setTimeout(() => resolve(fps), 3000);
  });
}

export async function getAdjustedFrameRate() {
  const possible_frame_rates = [24, 30, 60, 120, 144, 240, 480];
  let fps = await getFrameRate();
  return getClosestValue(fps, possible_frame_rates);
}

export async function endExperiment(props) {
  const el = jsPsych.getDisplayElement();
  jsPsych.data.addProperties(props);
  const {
    attention_check_failed,
    completion_code,
    debug_mode,
    demo_mode,
    redirect_url,
    images,
    platform,
    condition,
    worker_info,
  } = props;
  const data = insertInteractionData(jsPsych.data.get().json());

  if (debug_mode || demo_mode) {
    el.innerHTML = `<pre id="jspsych-data-display">${JSON.stringify(
      data,
      null,
      "\t",
    )}</pre>`;
    window.onbeforeunload = undefined;
    return;
  }

  try {
    console.log("jsPsych JSON data with interactions:", data);
    const result = await saveData({
      images,
      platform,
      worker_info,
      condition,
      data, // parse(data) // for csv
    });
    console.log("result", result);
    localStorage.clear();
  } catch (error) {
    console.log(error);
    window.onbeforeunload = undefined;
    return;
  }

  if (attention_check_failed) {
    el.innerHTML = `<p id="completionPara" class="jumbotron danger bg-danger text-white">
      You failed to complete the attention check correctly after multiple attempts; please return the HIT.
      </p>`;
    window.onbeforeunload = undefined;

    return;
  }

  if (redirect_url) {
    el.innerHTML = `<p id="completionPara" class="jumbotron alert alert-success bg-success text-white">
      Thanks for participating! You will be automatically redirected
      in a few moments to have your work submitted.
      If you have not been redirected to the submission step in
      a few moments,
      <a class="alert-link" href="${redirect_url}" target="_blank">click here</a>.
      </p>`;
    setTimeout(() => {
      window.location.href = redirect_url;
    }, 3000);
    return;
  }

  el.innerHTML = `<p id="completionPara" class="jumbotron success bg-success text-white">
    Thanks for participating! Your completion code is:
    <br><br>
    <strong><code class="text-white">${completion_code}</code></strong>
    <br><br>
    Please be sure to copy it into the corresponding box at the HIT
    to receive compensation!
    </p>`;
  window.onbeforeunload = undefined;
}

export async function getIpAddress() {
  let response = await fetch("/ip");
  return response.text();
}

export async function logVisitor(experiment_name, version_date) {
  const windowDimensions = [
    window.screen.width,
    window.screen.height,
    window.innerWidth,
    window.innerHeight,
  ];
  let ip_address = await getIpAddress();
  let data = [navigator.userAgent, windowDimensions, ip_address];
  let csv_line = data.join(",") + "\n";
  await saveData(
    experiment_name,
    `${experiment_name}_visitors_${version_date}.csv`,
    csv_line,
  );
}

export async function saveData({
  experiment_name,
  data,
  worker_info,
  platform,
  condition,
  max_retries = 10,
  wait_time = 2000,
  background_retry = false,
  contact_email = "stefan.uddenberg@chicagobooth.edu",
}) {
  console.log("data to send to server:", data);
  let saved_data =
    localStorage.getItem(`saved_data_${experiment_name}`) === "true";
  if (saved_data) console.log("Already saved!");
  let try_count = 0;
  if (platform === "prolific") {
    worker_info = {
      worker_id: worker_info.PROLIFIC_PID,
      hit_id: worker_info.STUDY_ID,
      assignment_id: worker_info.SESSION_ID,
    };
  } else if (platform === "turk") {
    worker_info = {
      worker_id: worker_info.workerId,
      hit_id: worker_info.hitId,
      assignment_id: worker_info.assignmentId,
    };
  } else if (platform === "connect") {
    worker_info = {
      worker_id: worker_info.participantId,
      hit_id: worker_info.projectId,
      assignment_id: worker_info.assignmentId,
    };
  } else {
    worker_info = {
      worker_id: worker_info.workerId || worker_info.worker_id,
      hit_id: worker_info.hitId || worker_info.hit_id,
      assignment_id: worker_info.assignmentId || worker_info.assignment_id,
    };
  }

  const { worker_id, hit_id, assignment_id } = worker_info;
  console.log("worker_info", worker_info);
  async function makeRequest() {
    console.log(`Making request ${try_count}...`);
    const result = await $.ajax({
      type: "post",
      contentType: "application/json; charset=UTF-8",
      async: true,
      cache: false,
      url: "/data", // path to the script that will handle saving data
      data: JSON.stringify({
        json_data: data,
        worker_id,
        assignment_id,
        hit_id,
        platform,
        condition,
      }),
    })
      .done(function (data) {
        localStorage.setItem(`saved_data_${experiment_name}`, true);
        console.log("Saved data", data);
      })
      .fail(async function (xhr, textStatus, error) {
        localStorage.setItem(`saved_data_${experiment_name}`, false);
        console.log("Error saving data", error);
        try_count++;
        let el = jsPsych.getDisplayElement();
        if (try_count <= max_retries) {
          if (!background_retry) {
            el.innerHTML = `<h1>Please wait; saving data...</h1>`;
          }
          await wait(makeRequest, wait_time);
        } else {
          if (!background_retry) {
            el.innerHTML = `<h1>Error saving data! Please contact your experimenter at ${contact_email}.</h1>`;
          }
          console.log("Reached max attempts!");
        }
      });
    return result;
  }
  const result = await makeRequest();
  return result;
}

export async function updateParticipantStatus({
  worker_info,
  platform = "turk",
  status = "working",
  max_retries = 10,
  wait_time = 2000,
}) {
  let try_count = 0;
  if (platform === "prolific") {
    worker_info = {
      worker_id: worker_info.PROLIFIC_PID,
      hit_id: worker_info.STUDY_ID,
      assignment_id: worker_info.SESSION_ID,
    };
  } else if (platform === "turk") {
    worker_info = {
      worker_id: worker_info.workerId,
      hit_id: worker_info.hitId,
      assignment_id: worker_info.assignmentId,
    };
  } else if (platform === "connect") {
    worker_info = {
      worker_id: worker_info.participantId,
      hit_id: worker_info.projectId,
      assignment_id: worker_info.assignmentId,
    };
  }

  console.log("worker_info", worker_info);
  const { worker_id, hit_id, assignment_id } = worker_info;
  console.log("worker_id", worker_id);
  async function makeRequest() {
    console.log(`Making request ${try_count}...`);
    const result = await $.ajax({
      type: "patch",
      contentType: "application/json; charset=UTF-8",
      async: true,
      cache: false,
      url: "/participants", // path to the script that will handle saving data
      data: JSON.stringify({
        worker_id,
        status,
      }),
    })
      .done(function (data) {
        console.log(`Updated status for ${worker_id} to ${status}`);
      })
      .fail(async function (xhr, textStatus, error) {
        console.log("Error updating participant", error);
        try_count++;
        let el = jsPsych.getDisplayElement();
        if (try_count <= max_retries) {
          await wait(makeRequest, wait_time);
        } else {
          console.error("Reached max attempts to update participant status!");
        }
      });
    return result;
  }
  const result = await makeRequest();
  return result;
}


export function setupFormValidation(formName) {
  $.validator.addMethod(
    "regex",
    function (value, element, regexp) {
      return this.optional(element) || regexp.test(value);
    },
    "Please check your input.",
  );

  $.validator.addMethod(
    "selectValidEntry",
    function (value, element, arg) {
      return value !== "NA" && value !== "";
    },
    "Please select a valid answer from the dropdown list.",
  );

  $.validator.addMethod("needsSelection", function (value, element) {
    const count = $(element).find("option:selected").length;
    return count > 0;
  });

  $("#race").bsMultiSelect({
    useCss: true,
  });

  $(`form[name='${formName}']`).validate({
    // Specify validation rules
    rules: {
      // The key name on the left side is the name attribute
      // of an input field. Validation rules are defined
      // on the right side

      attritionAnswer: {
        required: true,
        regex: /^\s*I will answer open-ended questions.\s*$/, // \s* : any number of white spaces
      },

      whatTested: {
        required: true,
        minlength: 5,
      },

      strategies: {
        required: true,
        minlength: 5,
      },

      estimatedPerformance: {
        required: true,
        min: 1,
        max: 100,
        digits: true,
      },

      seriousness: {
        required: true,
        min: 1,
        max: 100,
        digits: true,
      },

      interruption: {
        required: true,
        selectValidEntry: true,
      },

      participatedBefore: {
        required: true,
        selectValidEntry: true,
      },

      issues: {
        required: true,
        minlength: 2,
      },

      comments: {
        required: false,
      },

      age: {
        required: true,
        min: 18,
        max: 120,
        digits: true,
      },

      race: {
        needsSelection: true,
      },

      sex: {
        required: true,
        selectValidEntry: true,
      },

      gender: {
        required: true,
        minlength: 2,
      },
    },

    messages: {
      attritionAnswer: {
        required: "Please enter the highlighted text, including the period.",
        regex: "Please enter the highlighted text, including the period.",
      },

      age: {
        required: "Please enter your age",
        min: "Please enter a valid adult age",
        max: "Please enter a valid adult age",
      },

      race: {
        needsSelection: "Please select at least one race",
      },

      sex: {
        required: "Please select your sex",
      },

      gender: {
        required: "Please enter your self-identifed gender",
      },
    },

    ignore: ':hidden:not("#race")', // necessary due to bsMultiSelect

    // Highlight on error
    highlight: function (element, errorClass, validClass) {
      $(element).addClass("is-invalid");
    },

    // Remove error highlighting
    unhighlight: function (element, errorClass, validClass) {
      $(element).removeClass("is-invalid");
    },
  });

  $.validator.addClassRules("selectValidEntry", {
    selectValidEntry: true,
  });
}

export function getFormData(formId) {
  const inputs = $(`${formId} :input`);
  let formData = {};
  for (const input of inputs) {
    if (input.name === "") continue;
    formData[input.name] = $(input).val();
  }
  return formData;
}

export function initializeFormData(data) {
  if (data === null) {
    return;
  }
  // Assuming that each key is actually an input field id
  for (const [key, val] of Object.entries(data)) {
    $(`#${key}`).val(val);
  }
}

export function generateCompletionCode(prefix, suffix) {
  let code = "";
  for (const i of _.range(0, 10)) {
    let this_num = _.random(0, 9);
    let this_char = this_num.toString();
    code = code + this_char;
  }
  code = `${code}-${prefix}-`;

  for (let i of _.range(0, 10)) {
    let this_num = _.random(0, 9);
    let this_char = this_num.toString();
    code = code + this_char;
  }
  code = `${code}-${suffix}`;
  return code;
}
