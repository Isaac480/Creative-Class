import "jquery";
import "jquery-validation";
import seedrandom from "seedrandom";
import "lodash";
import LogRocket from "logrocket";
import moment from "moment/src/moment";
import Swal from "sweetalert2";
import {
  addTrialTypeDependencies,
  confirmExit,
  countInstructionsViewed,
  countPageRefreshes,
  endExperiment,
  generateCompletionCode,
  getFormData,
  getIpAddress,
  isBrowserSupported,
  setupFormValidation,
  updateParticipantStatus,
  getWorkerInfo,
} from "./utils";
import bundle from "jspsych/jspsych-bundler"; // where we define what plugins we use
import fullscreen from "jspsych/plugins/jspsych-fullscreen";
import render_mustache_template from "./render-mustache-template";
import external_html from "jspsych/plugins/jspsych-external-html";
import "jspsych/css/jspsych.css";
import "bootswatch/dist/flatly/bootstrap.min.css";
import "@dashboardcode/bsmultiselect/dist/css/BsMultiSelect.min.css";
import "../css/index.css";

export default async function runExperiment({
  consent_template = "consent.html",
  debug_mode = false,
  tags = ["{{", "}}"],
  preload_stimuli = [],
  logrocket_id,
  trial_types = [render_mustache_template],
  template_dir = "src/html",
  seed = Date.now(),
  show_progress_bar = true,
  instructions, // array of instructions pages
  worker_info,
  condition,
  generateTrials,
  experiment_name,
  experiment_title,
  version_date,
  intertrial_interval, // in ms
  estimated_task_duration = "15 minutes",
  compensation = "$2.50", // in dollars
  completion_code = generateCompletionCode("exa", "mple"),
  continue_button_name = "continueButton",
  consent_radio_button_name = "consentRadioButton",
  redact_worker_info = false,
  redirect_url = null,
}) {
  // * Set seed safely
  let orig_random = Math.random;
  seedrandom(seed, { global: true });
  _ = _.runInContext();
  Math.random = orig_random;

  // * Set experiment name
  if (localStorage.getItem("experiment_name") !== experiment_name)
    localStorage.clear();

  localStorage.setItem("experiment_name", experiment_name);
  localStorage.setItem("condition", condition);

  // * Set up jspsych
  const dependencies = [external_html, render_mustache_template, fullscreen];
  const jsPsych = bundle(addTrialTypeDependencies(dependencies, trial_types));
  const refresh_count = countPageRefreshes();
  const start_time = moment.utc().format();
  const anon_id = jsPsych.randomization.randomID(15);

  const platform = worker_info.platform;
  console.log("platform", platform);
  const cont_btn = continue_button_name;

  // * Log if possible
  if (logrocket_id) {
    LogRocket.init(logrocket_id);
    LogRocket.identify(anon_id, redact_worker_info ? {} : worker_info);
  }

  // * Check for valid browser
  const is_valid_browser = await isBrowserSupported();
  if (!is_valid_browser) {
    Swal.fire({
      icon: "error",
      title: "Browser not supported!",
      text: "Please try accessing this page from an updated Google Chrome browser.",
    });
    return;
  }

  // * Setup
  document.title = experiment_title;

  // * Set up trials
  const consent = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/${consent_template}`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      experiment_phase: "consent",
      refresh_count,
    },
    render_data: {
      compensation,
      duration: estimated_task_duration,
    },
    tags,
    check_fn() {
      const value = $(
        `input[name='${consent_radio_button_name}']:checked`
      ).val();
      if (value === "consent") {
        return true;
      }
      if (value === "reject") {
        window.onbeforeunload = undefined;
        window.location = "https://www.google.com";
      } else {
        alert(
          "You must check one of the boxes above to agree/disagree to participate in the research."
        );
      }
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_consent",
      });
    },
  };

  const fullscreen_start = {
    type: fullscreen.info.name,
    fullscreen_mode: true,
    message: `<p class="instructions text-left my-2">
      Thanks for agreeing to participate.
      Welcome! Before we begin, please close
      any other browser windows or tabs you
      currently have open, and set your mobile devices
      to silent, so that you can
      more easily pay attention to the task.
    </p>
    <p class="instructions text-left my-2">
      This experiment needs to be conducted in full screen mode.
      It will switch to full screen mode when you press the button below.
      Don't worry; we'll turn full screen off automatically for
      you at the end of the experiment.
    </p>`,
    on_finish(data) {
      data.screen_width = window.screen.width;
      data.screen_height = window.screen.height;
      data.window_width = window.innerWidth;
      data.window_height = window.innerHeight;
    },
    delay_after: intertrial_interval,
  };

  const fullscreen_end = {
    type: fullscreen.info.name,
    fullscreen_mode: false,
  };

  const attrition = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/attrition.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "attritionForm",
      form_id: "#attritionForm",
      experiment_phase: "attrition",
    },
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "attritionForm"],
    },
    tags,
    check_fn() {
      return $(this.data.form_id).valid();
    },
    on_finish(data) {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_attrition",
      });
      data.instructions_viewed_count = countInstructionsViewed();
    },
  };

  instructions = {
    ...instructions,
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_instructions",
      });
    },
  };

  const survey = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/survey.html`,
    cont_btn,
    post_trial_gap: intertrial_interval, // 0,
    data: {
      form_name: "surveyForm",
      form_id: "#surveyForm",
      experiment_phase: "survey",
    },
    render_data: {},
    tags,
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "surveyForm"],
    },
    check_fn() {
      const valid = $(this.data.form_id).valid();
      if (valid) {
        this.data.form_data = JSON.stringify(getFormData(this.data.form_id));
      }
      return valid;
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_survey",
      });
    },
  };

  const survey3 = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/survey3.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "survey3Form",
      form_id: "#survey3Form",
      experiment_phase: "survey",
    },
    tags,
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "survey3Form"],
    },
    check_fn() {
      const valid = $(this.data.form_id).valid();
      if (valid) {
        this.data.form_data = JSON.stringify(getFormData(this.data.form_id));
      }
      return valid;
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_survey",
      });
    },
  };

  const survey4 = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/survey4.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "survey4Form",
      form_id: "#survey4Form",
      experiment_phase: "survey",
    },
    tags,
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "survey4Form"],
    },
    check_fn() {
      const valid = $(this.data.form_id).valid();
      if (valid) {
        this.data.form_data = JSON.stringify(getFormData(this.data.form_id));
      }
      return valid;
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_survey",
      });
    },
  };

  const survey5 = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/survey5.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "survey5Form",
      form_id: "#survey5Form",
      experiment_phase: "survey",
    },
    tags,
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "survey5Form"],
    },
    check_fn() {
      const valid = $(this.data.form_id).valid();
      if (valid) {
        this.data.form_data = JSON.stringify(getFormData(this.data.form_id));
      }
      return valid;
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_survey",
      });
    },
  };

  const survey6 = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/survey6.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "survey6Form",
      form_id: "#survey6Form",
      experiment_phase: "survey",
    },
    tags,
    on_load_complete_callbacks: {
      setupFormValidation: [setupFormValidation, "survey6Form"],
    },
    check_fn() {
      const valid = $(this.data.form_id).valid();
      if (valid) {
        this.data.form_data = JSON.stringify(getFormData(this.data.form_id));
      }
      return valid;
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_survey",
      });
    },
  };

  const kai_questionnaire = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/kai-questionnaire.html`,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      form_name: "kaiForm",
      form_id: "#kaiForm",
      experiment_phase: "kai_questionnaire",
    },
    tags,
    check_fn() {
      return $(this.data.form_id).valid();
    },
    on_start() {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_task",
      });
    },
    on_finish(data) {
      updateParticipantStatus({
        worker_info,
        platform,
        status: "working_finished_kai_questionnaire",
      });
      data.form_data = JSON.stringify(getFormData(this.data.form_id));
    },
  };

  const debriefing = {
    type: render_mustache_template.info.name,
    url: `${template_dir}/debriefing.html`,
    render_data: { condition },
    tags,
    cont_btn,
    post_trial_gap: intertrial_interval,
    data: {
      completion_code,
      experiment_phase: "debriefing",
    },
  };

  const trials = await generateTrials();

  // * Timeline
  const timeline = [
    consent,
    fullscreen_start,
    attrition,
    instructions,
    ...trials,
    survey,
    survey3,
    survey4,
    survey5,
    survey6,
    //kai_questionnaire,
    debriefing,
    fullscreen_end,
  ];

  // * Start the experiment
  jsPsych.init({
    timeline,
    show_progress_bar,
    preload_images: preload_stimuli,
    async on_finish() {
      let orig_random = Math.random;
      seedrandom(Date.now(), { global: true });
      _ = _.runInContext();
      Math.random = orig_random;
      const ip_address = await getIpAddress();
      const opts = {
        experiment_name,
        ...(redact_worker_info ? {} : worker_info),
        start_time,
        condition,
        end_time: moment.utc().format(),
        total_time: jsPsych.totalTime(),
        ip_address,
        version_date,
        anon_id,
        debug_mode,
        refresh_count,
        completion_code,
        seed,
        redirect_url,
        worker_info,
        platform,
      };
      endExperiment(opts);
    },
  });

  window.onbeforeunload = confirmExit;
}
