export const handle = async ({ event, resolve }) => {
  return resolve(event, {
    preload: ({ type }) => type === "js" || type === "css",
  });
};
