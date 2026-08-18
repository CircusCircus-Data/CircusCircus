flowchart TD
    A["Visitor opens forum"] --> B["Browse subforums"]
    B --> C["View public post"]
    C --> D{"Logged in?"}

    D -- No --> E["Register or log in"]
    E --> F["Authenticated user"]

    D -- Yes --> F
    F --> G["Create post"]
    F --> H["Add comment"]
    F --> I["React to post"]
    F --> J["Update settings"]

    G --> K{"Post visibility"}
    K -- Public --> L["Visible to permitted visitors"]
    K -- Private --> M["Restricted by Flask route"]

    C --> N["Render Markdown"]
    C --> O["Display image or video"]

    F --> P["Direct messages"]