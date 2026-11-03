package it.samuele.nookcasa;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.view.ViewGroup;

/**
 * Settings page for Showcase Mode.
 * Each of the 4 cells has its own: Access Token (required), Device ID (optional),
 * API URL (optional, defaults to usetrmnl.com), and display name.
 */
public class ShowcaseSettingsActivity extends Activity {

    private static final int NUM_CELLS = ShowcaseActivity.NUM_CELLS;

    private EditText[] tokenFields = new EditText[NUM_CELLS];
    private EditText[] idFields    = new EditText[NUM_CELLS];
    private EditText[] urlFields   = new EditText[NUM_CELLS];
    private EditText[] nameFields  = new EditText[NUM_CELLS];

    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        FrameLayout root = new FrameLayout(this);
        root.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.FILL_PARENT,
                ViewGroup.LayoutParams.FILL_PARENT));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xFFFFFFFF);

        LinearLayout inner = new LinearLayout(this);
        inner.setOrientation(LinearLayout.VERTICAL);
        inner.setPadding(24, 24, 24, 24);

        TextView title = new TextView(this);
        title.setText("Showcase Settings");
        title.setTextSize(20);
        title.setTextColor(0xFF000000);
        inner.addView(title);

        TextView desc = new TextView(this);
        desc.setText("Configure each cell independently. Access Token is required. " +
                "Device ID is optional. API URL defaults to usetrmnl.com if left blank.");
        desc.setTextSize(12);
        desc.setTextColor(0xFF333333);
        LinearLayout.LayoutParams descParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.FILL_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        descParams.topMargin = 12;
        inner.addView(desc, descParams);

        String[] positions = { "top-left", "top-right", "bottom-left", "bottom-right" };

        for (int i = 0; i < NUM_CELLS; i++) {
            inner.addView(createSectionLabel("Cell " + (i + 1) + " (" + positions[i] + ")"));

            inner.addView(createLabel("Name (shown in grid)"));
            nameFields[i] = createTextField(ApiPrefs.getCellName(this, i));
            inner.addView(nameFields[i], createFieldParams());

            inner.addView(createLabel("Access Token (required)"));
            tokenFields[i] = createTextField(ApiPrefs.getShowcaseCellToken(this, i));
            inner.addView(tokenFields[i], createFieldParams());

            inner.addView(createLabel("Device ID (optional)"));
            idFields[i] = createTextField(ApiPrefs.getShowcaseCellId(this, i));
            inner.addView(idFields[i], createFieldParams());

            inner.addView(createLabel("API URL (optional, e.g. https://larapaper.bpmct.net/api)"));
            urlFields[i] = createTextField(ApiPrefs.getShowcaseCellUrl(this, i));
            inner.addView(urlFields[i], createFieldParams());
        }

        // Buttons
        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams actionsParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        actionsParams.topMargin = 20;
        inner.addView(actions, actionsParams);

        Button saveButton = new Button(this);
        saveButton.setText("Save");
        saveButton.setTextColor(0xFF000000);
        actions.addView(saveButton);

        Button backButton = new Button(this);
        backButton.setText("Back");
        backButton.setTextColor(0xFF000000);
        LinearLayout.LayoutParams backParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        backParams.leftMargin = 16;
        actions.addView(backButton, backParams);

        saveButton.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                save();
                android.content.Intent intent = new android.content.Intent(
                        ShowcaseSettingsActivity.this, ShowcaseActivity.class);
                intent.setFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP);
                startActivity(intent);
                finish();
            }
        });

        backButton.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                save();
                finish();
            }
        });

        scroll.addView(inner);

        // No rotation — keep native orientation for keyboard compatibility
        root.addView(scroll, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.FILL_PARENT,
                ViewGroup.LayoutParams.FILL_PARENT));
        setContentView(root);
    }

    private void save() {
        for (int i = 0; i < NUM_CELLS; i++) {
            ApiPrefs.setCellName(this, i, nameFields[i].getText().toString().trim());
            ApiPrefs.setShowcaseCellToken(this, i, tokenFields[i].getText().toString().trim());
            ApiPrefs.setShowcaseCellId(this, i, idFields[i].getText().toString().trim());
            ApiPrefs.setShowcaseCellUrl(this, i, urlFields[i].getText().toString().trim());
        }
        // Clear cache so cells reload with new credentials
        ShowcaseActivity.clearCache(this);
    }

    private TextView createSectionLabel(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextSize(13);
        label.setTextColor(0xFF000000);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = 20;
        label.setLayoutParams(params);
        return label;
    }

    private TextView createLabel(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextSize(12);
        label.setTextColor(0xFF000000);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = 14;
        label.setLayoutParams(params);
        return label;
    }

    private EditText createTextField(String value) {
        EditText field = new EditText(this);
        field.setTextColor(0xFF000000);
        field.setBackgroundColor(0xFFEEEEEE);
        field.setPadding(12, 8, 12, 8);
        field.setSingleLine(true);
        if (value != null) field.setText(value);
        return field;
    }

    private LinearLayout.LayoutParams createFieldParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.FILL_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = 4;
        return params;
    }
}
