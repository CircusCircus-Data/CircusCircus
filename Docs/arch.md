classDiagram
    direction TB

    class FlaskApplication {
        <<complete>>
        +create_app()
        +register_blueprints()
        +initialize_database()
        +create_tables()
    }

    class Config {
        <<complete>>
        +SECRET_KEY
        +FLASK_APP
        +SQLALCHEMY_DATABASE_URI
        +load_environment()
    }

    class AuthBlueprint {
        <<complete>>
        +loginform()
        +action_login()
        +action_logout()
        +action_createaccount()
    }

    class PostsBlueprint {
        <<complete>>
        +subforum()
        +addpost()
        +viewpost()
        +action_post()
    }

    class CommentsBlueprint {
        <<complete>>
        +add_comment()
    }

    class ReactionsBlueprint {
        <<in progress>>
        +add_reaction()
        +change_reaction()
        +count_reactions()
    }

    class SettingsBlueprint {
        <<planned>>
        +view_settings()
        +update_account()
    }

    class MessagesBlueprint {
        <<stretch goal>>
        +inbox()
        +view_conversation()
        +send_message()
    }

    class ContentService {
        <<planned>>
        +render_markdown()
        +sanitize_html()
        +validate_image_link()
        +validate_video_link()
    }

    class Templates {
        <<in progress>>
        +layout
        +login
        +subforums
        +subforum
        +createpost
        +viewpost
        +settings
        +messages
    }

    class BootstrapUI {
        <<planned>>
        +responsive_navigation
        +styled_forms
        +post_cards
        +comment_cards
        +reaction_buttons
        +logo
        +footer
    }

    class MySQLDatabase {
        <<complete>>
        +database: circuscircus
        +user: circus_app
        +version: MySQL 8.4
    }

    FlaskApplication --> Config : loads
    Config --> MySQLDatabase : connects

    FlaskApplication --> AuthBlueprint : registers
    FlaskApplication --> PostsBlueprint : registers
    FlaskApplication --> CommentsBlueprint : registers
    FlaskApplication --> ReactionsBlueprint : registers
    FlaskApplication --> SettingsBlueprint : will register
    FlaskApplication --> MessagesBlueprint : may register

    PostsBlueprint --> ContentService : will use
    Templates --> BootstrapUI : will use

    AuthBlueprint --> MySQLDatabase : users
    PostsBlueprint --> MySQLDatabase : posts
    CommentsBlueprint --> MySQLDatabase : comments
    ReactionsBlueprint --> MySQLDatabase : reactions
    SettingsBlueprint --> MySQLDatabase : user settings
    MessagesBlueprint --> MySQLDatabase : messages