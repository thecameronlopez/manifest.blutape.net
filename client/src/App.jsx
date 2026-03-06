import React from "react";
import {
  Route,
  RouterProvider,
  createBrowserRouter,
  createRoutesFromElements,
} from "react-router-dom";
import RootLayout from "./layout/RootLayout";
import NewManifest from "./routes/upload/NewManifest";
import Search from "./routes/search/Search";
import Manifest from "./routes/manifest/Manifest";
import CreateManifest from "./routes/create/CreateManifest";

const App = () => {
  const router = createBrowserRouter(
    createRoutesFromElements(
      <Route path="/" element={<RootLayout />}>
        <Route index element={<NewManifest />} />
        <Route path="new-manifest" element={<NewManifest />} />
        <Route path="create-manifest" element={<CreateManifest />} />
        <Route path="search" element={<Search />} />
        <Route path="manifest/:id" element={<Manifest />} />
      </Route>,
    ),
  );
  return <RouterProvider router={router} />;
};

export default App;
