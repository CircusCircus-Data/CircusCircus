classDiagram
    direction TB

    class User {
        <<complete>>
        +Integer id
        +String username
        +String password_hash
        +String email
        +Boolean admin
        +check_password()
    }

    class Subforum {
        <<complete>>
        +Integer id
        +String title
        +Text description
        +Integer parent_id
        +Boolean hidden
    }

    class Post {
        <<partially complete>>
        +Integer id
        +String title
        +Text content
        +DateTime postdate
        +Integer user_id
        +Integer subforum_id
        +String visibility
        +String image_url
        +String video_url
        +get_time_string()
    }

    class Comment {
        <<complete>>
        +Integer id
        +Text content
        +DateTime postdate
        +Integer user_id
        +Integer post_id
        +get_time_string()
    }

    class Reaction {
        <<in progress>>
        +Integer id
        +String reaction_type
        +Integer user_id
        +Integer post_id
        +Unique user_id and post_id
    }

    class UserSettings {
        <<planned>>
        +Integer id
        +Integer user_id
        +update_username()
        +update_email()
    }

    class Message {
        <<stretch goal>>
        +Integer id
        +Text content
        +DateTime sent_at
        +Boolean is_read
        +Integer sender_id
        +Integer recipient_id
    }

    User "1" --> "0..*" Post : creates
    User "1" --> "0..*" Comment : writes
    User "1" --> "0..*" Reaction : selects
    User "1" --> "0..1" UserSettings : owns

    Subforum "0..1" --> "0..*" Subforum : contains
    Subforum "1" --> "0..*" Post : contains

    Post "1" --> "0..*" Comment : receives
    Post "1" --> "0..*" Reaction : receives

    User "1" --> "0..*" Message : sends
    User "1" --> "0..*" Message : receives