/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import React from "react";
import Typography from "@material-ui/core/Typography";
import Divider from "@material-ui/core/Divider";
import TokenPermission from "./TokenPermission";
import TextField from "@material-ui/core/TextField";
import Grid from "@material-ui/core/Grid";
import { DateTimePicker, MuiPickersUtilsProvider } from "material-ui-pickers";
import DateFnsUtils from "@date-io/date-fns";
import { getMyRightsForServer, createToken } from "./util/api";
import PropTypes from "prop-types";
import { withStyles } from "@material-ui/core/styles";
import SubmitButtons from "./SubmitButtons";
import ServerAggregationUnits from "./ServerAggregationUnits";
import ExpansionPanel from "@material-ui/core/ExpansionPanel";
import ExpansionPanelSummary from "@material-ui/core/ExpansionPanelSummary";
import ExpansionPanelDetails from "@material-ui/core/ExpansionPanelDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Checkbox from "@material-ui/core/Checkbox";
import WarningDialog from "./WarningDialog";

const styles = theme => ({
  root: {
    ...theme.mixins.gutters(),
    paddingTop: theme.spacing.unit * 2,
    paddingBottom: theme.spacing.unit * 2
  },
  heading: {
    fontSize: theme.typography.pxToRem(18),
    fontWeight: theme.typography.alignCenter
  }
});
class TokenDetails extends React.Component {
  constructor(props) {
    super(props);
    this.nameRef = React.createRef();
  }
  state = {
    nickName: {},
    rights: {},
    expiry: new Date(),
    latest_expiry: new Date(),
    name_helper_text: "",
    isPermissionChecked: true,
    isAggregationChecked: true,
    permissionIndeterminate: false,
    aggregateIndeterminate: false,
    totalAggregateUnits: 0,
    uiReady: new Promise(() => {}),
    pageError: false,
    errors: { message: "" }
  };
  completeToken = () => {
    const { name, expiry, rights } = this.state;
    const { serverID, cancel } = this.props;
    createToken(name, serverID, new Date(expiry).toISOString(), rights).then(
      json => {
        cancel();
      }
    );
  };
  handleSubmit = async () => {
    const { name, name_helper_text, uiReady } = this.state;
    await uiReady;
    const checkedCheckboxes = document.querySelectorAll(
      'input[type="checkbox"]:checked'
    );
    if (name && name_helper_text === "" && checkedCheckboxes.length != 0) {
      this.completeToken();
    } else if (checkedCheckboxes.length == 0) {
      this.setState({
        pageError: true,
        errors: {
          message:
            "Warning: no permissions will be granted by this token. Are you sure?"
        }
      });
    } else if (!name) {
      this.setState({
        name_helper_text: "Token name cannot be blank."
      });
      this.scrollToRef(this.nameRef);
    }
  };

  handleDateChange = date => {
    this.setState(Object.assign(this.state, { expiry: date }));
  };

  handleChange = (claim, right) => event => {
    this.setState({ pageError: false, errors: "" });
    const { rights } = this.state;

    rights[claim].permissions[right] = event.target.checked;
    const permissionSet = new Set();
    for (const keys in rights) {
      for (const key in rights[keys].permissions) {
        permissionSet.add(rights[keys].permissions[key]);
      }
    }
    const indeterminate = permissionSet.size > 1;
    console.log(indeterminate);
    this.setState({ rights: rights, permissionIndeterminate: indeterminate });
  };
  scrollToRef = ref => ref.current.scrollIntoView();

  handleAggUnitChange = (claim_id, claim, unit) => event => {
    this.setState({ pageError: false, errors: "" });
    const { rights, totalAggregateUnits } = this.state;
    if (event.target.checked) {
      rights[claim].spatial_aggregation.push(unit);
    } else {
      rights[claim].spatial_aggregation = rights[
        claim
      ].spatial_aggregation.filter(u => u != unit);
    }
    console.log(rights);
    const listUnits = [];
    for (const key in rights) {
      for (const keys in rights[key].spatial_aggregation) {
        listUnits.push(keys);
      }
    }

    this.setState({
      rights: rights,
      aggregateIndeterminate: totalAggregateUnits != listUnits.length
    });
  };
  handlePermissionCheckbox = async event => {
    const toCheck = event.target.checked;
    event.stopPropagation();
    const { uiReady } = this.state;
    this.setState({
      isPermissionChecked: toCheck,
      permissionIndeterminate: false,
      pageError: false,
      errors: ""
    });
    await uiReady; // Wait to make sure checkboxes exist
    const { rights } = this.state;

    for (const keys in rights) {
      for (const key in rights[keys].permissions) {
        rights[keys].permissions[key] = toCheck;
      }
    }
    this.setState({
      rights: rights
    });
  };
  handleAggregationCheckbox = async event => {
    const toCheck = event.target.checked;
    this.setState({
      pageError: false,
      errors: "",
      isAggregationChecked: toCheck,
      aggregateIndeterminate: false
    });
    event.stopPropagation();
    const { uiReady } = this.state;
    await uiReady; // Wait to make sure checkboxes exist
    var listUnits = [];
    const { rights, permitted } = this.state;
    for (const key in rights) {
      if (toCheck) {
        rights[key].spatial_aggregation = permitted[key].spatial_aggregation;
      } else {
        rights[key].spatial_aggregation = [];
      }
      for (const keys in rights[key].spatial_aggregation) {
        listUnits.push(keys);
      }
    }
    this.setState({
      rights: rights
    });
  };
  handleNameChange = event => {
    var letters = /^[A-Za-z0-9_]+$/;
    let name = event.target.value;
    if (name.match(letters)) {
      this.setState(
        Object.assign(this.state, {
          name_helper_text: ""
        })
      );
    } else if (name.length == 0) {
      this.setState(
        Object.assign(this.state, {
          name_helper_text: "Token name cannot be blank."
        })
      );
    } else {
      this.setState(
        Object.assign(this.state, {
          name_helper_text:
            "Token name may only contain letters, numbers and underscores."
        })
      );
    }
    this.setState({ name: event.target.value });
  };

  isAggUnitPermitted = (claim, key) => {
    const { permitted } = this.state;
    return permitted[claim].spatial_aggregation.indexOf(key) !== -1;
  };

  componentDidMount() {
    this.setState({
      uiReady: getMyRightsForServer(this.props.serverID)
        .then(json => {
          const totalAggUnits = Object.keys(json.allowed_claims).reduce(
            (acc, k) => acc + json.allowed_claims[k].spatial_aggregation.length,
            0
          );

          this.setState({
            rights: JSON.parse(JSON.stringify(json.allowed_claims || {})),
            permitted: json.allowed_claims || {},
            expiry: json.latest_expiry,
            latest_expiry: json.latest_expiry,
            totalAggregateUnits: totalAggUnits
          });
        })
        .catch(err => {
          this.setState({ hasError: true, error: err });
        })
    });
  }

  renderRights = () => {
    var perms = [];
    const { rights, permitted } = this.state;
    for (const key in rights) {
      perms.push([
        <TokenPermission
          permissions={rights[key].permissions}
          claim={key}
          checkedHandler={this.handleChange}
          permitted={permitted[key].permissions}
        />,
        key
      ]);
    }
    return perms
      .sort((a, b) => {
        if (a[1] > b[1]) {
          return 1;
        } else if (a[1] < b[1]) {
          return -1;
        } else {
          return 0;
        }
      })
      .map(x => x[0]);
  };

  renderAggUnits = () => {
    var perms = [];
    const { rights, permitted, isAggregationChecked } = this.state;
    for (const key in rights) {
      perms.push([
        <ServerAggregationUnits
          units={rights[key].spatial_aggregation}
          claim={key}
          checkedHandler={this.handleAggUnitChange}
          permitted={this.isAggUnitPermitted}
        />,
        key
      ]);
    }
    return perms
      .sort((a, b) => {
        if (a[1] > b[1]) {
          return 1;
        } else if (a[1] < b[1]) {
          return -1;
        } else {
          return 0;
        }
      })
      .map(x => x[0]);
  };

  render() {
    if (this.state.hasError) throw this.state.error;

    const {
      expiry,
      latest_expiry,
      name,
      aggregateIndeterminate,
      isAggregationChecked,
      isPermissionChecked,
      permissionIndeterminate,
      name_helper_text
    } = this.state;
    const { classes, onClick } = this.props;

    return (
      <React.Fragment>
        <div ref={this.nameRef} />
        <Grid item xs={12}>
          <Typography variant="h5" component="h1">
            Token Name
          </Typography>
        </Grid>
        <Divider />
        <Grid item xs={12}>
          <TextField
            id="name"
            label="Name"
            className={classes.textField}
            value={name}
            onChange={this.handleNameChange}
            margin="normal"
            error={name_helper_text !== ""}
            helperText={name_helper_text}
          />
        </Grid>
        <Grid item xs={12}>
          <Typography variant="h5" component="h1">
            Token Expiry
          </Typography>
        </Grid>
        <Divider />
        <Grid item xs>
          <MuiPickersUtilsProvider utils={DateFnsUtils}>
            <DateTimePicker
              value={expiry}
              onChange={this.handleDateChange}
              disablePast={true}
              maxDate={latest_expiry}
              format="yyyy/MM/dd HH:mm:ss"
              ampm={false}
              margin="normal"
              helperText={new Date().toTimeString().slice(9)} // Display the timezone
            />
          </MuiPickersUtilsProvider>
        </Grid>
        <Grid item xs={12}>
          <ExpansionPanel>
            <ExpansionPanelSummary expandIcon={<ExpandMoreIcon id="api-exp" />}>
              <Checkbox
                checked={isPermissionChecked}
                indeterminate={permissionIndeterminate}
                data-cy="permissions-top-level"
                id="permissions"
                value="checkedB"
                color="primary"
                onClick={this.handlePermissionCheckbox}
              />

              <Grid item xs={2}>
                <Typography
                  className={classes.heading}
                  style={{ paddingTop: 10 }}
                >
                  API Permissions
                </Typography>
              </Grid>
            </ExpansionPanelSummary>
            <ExpansionPanelDetails>
              <Grid container spacing={5}>
                {this.renderRights()}
              </Grid>
            </ExpansionPanelDetails>
          </ExpansionPanel>
          <ExpansionPanel>
            <ExpansionPanelSummary
              expandIcon={<ExpandMoreIcon id="unit-exp" />}
            >
              <Checkbox
                id="units"
                checked={isAggregationChecked}
                indeterminate={aggregateIndeterminate}
                value="checkedB"
                color="primary"
                onClick={this.handleAggregationCheckbox}
              />

              <Grid item xs={3}>
                <Typography
                  className={classes.heading}
                  style={{ paddingTop: 10 }}
                >
                  Aggregation Units
                </Typography>
              </Grid>
            </ExpansionPanelSummary>
            <ExpansionPanelDetails>
              <Grid container spacing={5}>
                {this.renderAggUnits()}
              </Grid>
            </ExpansionPanelDetails>
          </ExpansionPanel>
        </Grid>
        <WarningDialog
          open={this.state.pageError}
          message={this.state.errors.message}
          handleClick={this.completeToken}
        />
        <SubmitButtons handleSubmit={this.handleSubmit} onClick={onClick} />
      </React.Fragment>
    );
  }
}

TokenDetails.propTypes = {
  classes: PropTypes.object.isRequired
};

export default withStyles(styles)(TokenDetails);
