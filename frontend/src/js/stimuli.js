import "lodash";

export function getStimuli({
  image_dir = "src/images",
  num_stimuli = 2,
  extension = ".jpg",
  filenames = null,
}) {
  if (filenames) {
    return _.map(filenames, (name) => `${image_dir}/${name}`);
  }
  return _.map(
    _.range(1, num_stimuli + 1),
    (i) => `${image_dir}/${i}${extension}`,
  );
}

export function getMorphStimuli({
  image_dir = "src/images/06F-21M/disgust",
  condition = "disgust",
  num_stimuli = 61,
  extension = ".jpg",
}) {
  return _.map(
    _.range(1, num_stimuli + 1),
    (i) =>
      `${image_dir}/${condition}_${i.toString().padStart(2, "0")}${extension}`,
  );
}
